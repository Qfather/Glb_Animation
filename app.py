# -*- coding: utf-8 -*-
"""本地 GLB 动画资产 WebUI。运行后通过浏览器上传，再手动提交整个目录到 GitHub。"""
import json, re, uuid, webbrowser
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data.json"
DEFAULT_RACES=["人类","兽人","精灵","机器人","中性","其他"]
app=Flask(__name__, static_folder=None)

def read_data():
    try: return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception: return {"version":1,"generated_at":"","items":[],"enums":{"sources":[],"races":DEFAULT_RACES,"tags":[]}}

def safe_name(value):
    value=re.sub(r"[^\w\u4e00-\u9fff-]+","-",value.strip()).strip("-")[:70]
    return value or "animation"

@app.get("/api/status")
def status(): return jsonify(local=True)

@app.get("/api/items")
def items(): return jsonify(read_data())

@app.post("/api/upload")
def upload():
    name=(request.form.get("name") or "").strip()
    race=request.form.get("race") or ""
    preview=request.files.get("preview")
    glb=request.files.get("glb")
    if not name: return jsonify(error="名称不能为空"),400
    if race not in DEFAULT_RACES and race not in read_data().get("enums",{}).get("races",[]): return jsonify(error="种族无效"),400
    if not preview or Path(preview.filename or "").suffix.lower()!=".webp": return jsonify(error="预览图必须是 WEBP"),400
    if not glb or Path(glb.filename or "").suffix.lower()!=".glb": return jsonify(error="动画文件必须是 GLB"),400
    tags=[x.strip() for x in (request.form.get("tags") or "").split(",") if x.strip()]
    key=f"assets/{race}/{safe_name(name)}"
    folder=ROOT/key; folder.mkdir(parents=True,exist_ok=True)
    preview.save(folder/"preview.webp"); glb.save(folder/(safe_name(name)+".glb"))
    item={"id":str(uuid.uuid4()),"index":int(datetime.now().timestamp()*1000),"name":name,"source":request.form.get("source") or "","race":race,"tags":tags,"category":"","preview_url":f"{key}/preview.webp","glb_url":f"{key}/{safe_name(name)}.glb"}
    (folder/"meta.json").write_text(json.dumps(item,ensure_ascii=False,indent=1),encoding="utf-8")
    data=read_data();data["items"]=[*data.get("items",[]),item];enums=data.setdefault("enums",{});enums["races"]=sorted(set(enums.get("races",DEFAULT_RACES)));enums["tags"]=sorted(set(enums.get("tags",[])+tags));data["generated_at"]=datetime.now().isoformat(timespec="seconds")
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(item=item)

@app.route("/api/enums", methods=["POST", "PUT", "DELETE"])
def add_enum():
    body=request.get_json(silent=True) or {}; kind=body.get("kind"); value=(body.get("value") or "").strip(); old=(body.get("old") or "").strip()
    if kind not in ("sources","races","tags") or not value: return jsonify(error="枚举参数无效"),400
    data=read_data(); enums=data.setdefault("enums",{}); values=list(enums.get(kind,DEFAULT_RACES if kind=="races" else []))
    if request.method=="PUT":
        if not old or old not in values: return jsonify(error="原枚举不存在"),404
        if value in values and value!=old: return jsonify(error="新名称已存在"),400
        values=[value if x==old else x for x in values]
        for item in data.get("items",[]):
            field="race" if kind=="races" else ("source" if kind=="sources" else "tags")
            if kind=="tags": item["tags"]=[value if x==old else x for x in item.get("tags",[])]
            elif item.get(field)==old: item[field]=value
    elif request.method=="DELETE":
        if any((value in item.get("tags",[]) if kind=="tags" else item.get("race" if kind=="races" else "source")==value) for item in data.get("items",[])): return jsonify(error="该枚举仍被动画使用，不能删除"),400
        values=[x for x in values if x!=value]
    elif value not in values: values.append(value)
    enums[kind]=sorted(set(values)); DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    for item in data.get("items",[]):
        folder=ROOT/Path(item["preview_url"]).parent
        if (folder/"meta.json").exists(): (folder/"meta.json").write_text(json.dumps(item,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(enums=enums)

@app.put("/api/items/<item_id>")
def edit_item(item_id):
    data=read_data(); item=next((x for x in data.get("items",[]) if x.get("id")==item_id),None)
    if not item: return jsonify(error="找不到动画"),404
    name=(request.form.get("name") or "").strip()
    race=request.form.get("race") or ""
    if not name or race not in read_data().get("enums",{}).get("races",DEFAULT_RACES): return jsonify(error="名称或种族无效"),400
    item.update(name=name,source=request.form.get("source") or "",race=race,tags=[x.strip() for x in (request.form.get("tags") or "").split(",") if x.strip()]); item.pop("gender",None)
    folder=ROOT/Path(item["preview_url"]).parent
    if request.files.get("preview"): request.files["preview"].save(folder/"preview.webp")
    if request.files.get("glb"):
        request.files["glb"].save(folder/(safe_name(name)+".glb")); item["glb_url"]=f"{Path(item['preview_url']).parent.as_posix()}/{safe_name(name)}.glb"
    data["generated_at"]=datetime.now().isoformat(timespec="seconds"); DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8"); (folder/"meta.json").write_text(json.dumps(item,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(item=item)

@app.get("/")
def index(): return send_from_directory(ROOT,"index.html")

@app.get("/<path:path>")
def files(path): return send_from_directory(ROOT,path)

if __name__=="__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1",port=5000,debug=False)
