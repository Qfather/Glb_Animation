# -*- coding: utf-8 -*-
"""本地 GLB 动画资产 WebUI。运行后通过浏览器上传，再手动提交整个目录到 GitHub。"""
import json, re, uuid, webbrowser, shutil
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data.json"
DEFAULT_RACES=["人类","兽人","精灵","机器人","中性","其他"]
DEFAULT_FPS=["30","60"]
DEFAULT_WEAPONS=["单手","双手","手枪"]
app=Flask(__name__, static_folder=None)

def read_data():
    try: data=json.loads(DATA.read_text(encoding="utf-8"))
    except Exception: data={"version":1,"generated_at":"","items":[],"enums":{"sources":[],"races":DEFAULT_RACES,"tags":[],"fps":DEFAULT_FPS,"weapons":DEFAULT_WEAPONS}}
    enums=data.setdefault("enums",{}); changed=False
    weapons=list(enums["weapons"]) if "weapons" in enums else list(DEFAULT_WEAPONS)
    tags=[x for x in enums.get("tags",[]) if x not in DEFAULT_WEAPONS]
    if weapons!=enums.get("weapons") or tags!=enums.get("tags"): enums["weapons"]=weapons; enums["tags"]=tags; changed=True
    for item in data.get("items",[]):
        old_tags=item.get("tags",[]); item_weapons=list(dict.fromkeys(item.get("weapons",[])+[x for x in old_tags if x in DEFAULT_WEAPONS])); new_tags=[x for x in old_tags if x not in DEFAULT_WEAPONS]
        if item_weapons!=item.get("weapons") or new_tags!=old_tags: item["weapons"]=item_weapons; item["tags"]=new_tags; changed=True
    if changed: DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    return data

def safe_name(value):
    value=re.sub(r"[^\w\u4e00-\u9fff-]+","-",value.strip()).strip("-")[:70]
    return value or "animation"

def unique_name(name, items):
    used={str(item.get("name") or "") for item in items}
    if name not in used: return name
    number=1
    while f"{name}_{number:03d}" in used: number+=1
    return f"{name}_{number:03d}"

@app.get("/api/status")
def status(): return jsonify(local=True)

@app.get("/api/items")
def items(): return jsonify(read_data())

@app.post("/api/upload")
def upload():
    name=(request.form.get("name") or "").strip()
    source=request.form.get("source") or ""
    race=request.form.get("race") or ""
    preview=request.files.get("preview")
    glb=request.files.get("glb")
    if not name: return jsonify(error="名称不能为空"),400
    if source not in read_data().get("enums",{}).get("sources",[]): return jsonify(error="来源必须选择有效枚举"),400
    if race not in DEFAULT_RACES and race not in read_data().get("enums",{}).get("races",[]): return jsonify(error="种族无效"),400
    if not preview or Path(preview.filename or "").suffix.lower()!=".webp": return jsonify(error="预览图必须是 WEBP"),400
    if not glb or Path(glb.filename or "").suffix.lower()!=".glb": return jsonify(error="动画文件必须是 GLB"),400
    data=read_data(); name=unique_name(name,data.get("items",[]))
    tags=[x.strip() for x in (request.form.get("tags") or "").split(",") if x.strip()]
    weapons=[x.strip() for x in (request.form.get("weapons") or "").split(",") if x.strip()]
    if any(x not in data.get("enums",{}).get("weapons",DEFAULT_WEAPONS) for x in weapons): return jsonify(error="武器标签无效"),400
    key=f"assets/{safe_name(race)}/{safe_name(name)}"
    folder=ROOT/key; folder.mkdir(parents=True,exist_ok=True)
    preview.save(folder/"preview.webp"); glb.save(folder/(safe_name(name)+".glb"))
    fps=request.form.get("fps") or DEFAULT_FPS[0]
    data=read_data()
    if fps not in data.get("enums",{}).get("fps",DEFAULT_FPS): return jsonify(error="FPS 无效"),400
    item={"id":str(uuid.uuid4()),"index":int(datetime.now().timestamp()*1000),"name":name,"source":source,"race":race,"fps":fps,"tags":tags,"weapons":weapons,"category":"","preview_url":f"{key}/preview.webp","glb_url":f"{key}/{safe_name(name)}.glb"}
    (folder/"meta.json").write_text(json.dumps(item,ensure_ascii=False,indent=1),encoding="utf-8")
    data["items"]=[*data.get("items",[]),item];enums=data.setdefault("enums",{});enums["races"]=list(dict.fromkeys([*enums.get("races",DEFAULT_RACES),race]));enums["fps"]=list(dict.fromkeys([*enums.get("fps",DEFAULT_FPS),fps]));enums["tags"]=list(dict.fromkeys([*enums.get("tags",[]),*tags]));enums["weapons"]=list(dict.fromkeys([*enums.get("weapons",DEFAULT_WEAPONS),*weapons]));data["generated_at"]=datetime.now().isoformat(timespec="seconds")
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(item=item)

@app.route("/api/enums", methods=["POST", "PUT", "DELETE"])
def add_enum():
    body=request.get_json(silent=True) or {}; kind=body.get("kind"); value=(body.get("value") or "").strip(); old=(body.get("old") or "").strip(); force=bool(body.get("force"))
    if kind not in ("sources","races","weapons","tags","fps") or not value: return jsonify(error="枚举参数无效"),400
    data=read_data(); enums=data.setdefault("enums",{}); values=list(enums.get(kind,DEFAULT_FPS if kind=="fps" else DEFAULT_RACES if kind=="races" else []))
    if request.method=="PUT":
        if not old or old not in values: return jsonify(error="原枚举不存在"),404
        if value in values and value!=old: return jsonify(error="新名称已存在"),400
        values=[value if x==old else x for x in values]
        for item in data.get("items",[]):
            field="race" if kind=="races" else ("source" if kind=="sources" else "fps" if kind=="fps" else "weapons" if kind=="weapons" else "tags")
            if kind in ("tags","weapons"): item[field]=[value if x==old else x for x in item.get(field,[])]
            elif item.get(field)==old: item[field]=value
    elif request.method=="DELETE":
        field="tags" if kind=="tags" else "weapons" if kind=="weapons" else "race" if kind=="races" else "source"
        used=[item for item in data.get("items",[]) if (value in item.get(field,[]) if kind in ("tags","weapons") else item.get(field)==value)]
        if used and kind not in ("tags","weapons"): return jsonify(error="该枚举仍被动画使用，不能删除",used=[item.get("name") for item in used]),400
        if used and not force: return jsonify(error="该标签正在被以下动画使用",used=[item.get("name") for item in used],confirm=True),409
        if kind in ("tags","weapons"):
            for item in used: item[field]=[tag for tag in item.get(field,[]) if tag!=value]
        values=[x for x in values if x!=value]
    elif value not in values: values.append(value)
    enums[kind]=list(dict.fromkeys(values)); DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    for item in data.get("items",[]):
        folder=ROOT/Path(item["preview_url"]).parent
        if (folder/"meta.json").exists(): (folder/"meta.json").write_text(json.dumps(item,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(enums=enums)

@app.put("/api/enums/order")
def reorder_enum():
    body=request.get_json(silent=True) or {}; kind=body.get("kind"); order=body.get("values") or []
    if kind not in ("sources","races","weapons","tags","fps") or not isinstance(order,list): return jsonify(error="排序参数无效"),400
    data=read_data(); current=list(data.setdefault("enums",{}).get(kind,[])); ordered=list(dict.fromkeys([x for x in order if x in current] + current))
    if set(ordered)!=set(current): return jsonify(error="排序内容不完整"),400
    data["enums"][kind]=ordered; DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(enums=data["enums"])

@app.put("/api/items/<item_id>")
def edit_item(item_id):
    data=read_data(); item=next((x for x in data.get("items",[]) if x.get("id")==item_id),None)
    if not item: return jsonify(error="找不到动画"),404
    name=(request.form.get("name") or "").strip()
    source=request.form.get("source") or ""
    race=request.form.get("race") or ""
    enums=read_data().get("enums",{})
    if not name or source not in enums.get("sources",[]) or race not in enums.get("races",DEFAULT_RACES): return jsonify(error="名称、来源或种族无效"),400
    name=unique_name(name,[x for x in data.get("items",[]) if x.get("id")!=item_id])
    fps=request.form.get("fps") or str(item.get("fps") or "30")
    if fps not in read_data().get("enums",{}).get("fps",DEFAULT_FPS): return jsonify(error="FPS 无效"),400
    old_folder=ROOT/Path(item["preview_url"]).parent
    old_glb_path=ROOT/Path(item.get("glb_url", ""))
    tags=[x.strip() for x in (request.form.get("tags") or "").split(",") if x.strip()]
    weapons=[x.strip() for x in (request.form.get("weapons") or "").split(",") if x.strip()]
    if any(x not in enums.get("weapons",DEFAULT_WEAPONS) for x in weapons): return jsonify(error="武器标签无效"),400
    item.update(name=name,source=source,race=race,fps=fps,tags=tags,weapons=weapons); item.pop("gender",None)
    new_folder=ROOT/"assets"/safe_name(race)/safe_name(name)
    if old_folder.resolve()!=new_folder.resolve():
        if new_folder.exists(): return jsonify(error="目标种族下已存在同名资产"),400
        new_folder.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(old_folder),str(new_folder))
    folder=new_folder
    item["preview_url"]=(Path("assets")/safe_name(race)/safe_name(name)/"preview.webp").as_posix()
    if request.files.get("preview"): request.files["preview"].save(folder/"preview.webp")
    old_glb=folder/old_glb_path.name
    new_glb=folder/(safe_name(name)+".glb")
    if request.files.get("glb"):
        request.files["glb"].save(new_glb)
    elif old_glb.exists() and old_glb.resolve()!=new_glb.resolve(): old_glb.rename(new_glb)
    item["glb_url"]=(Path("assets")/safe_name(race)/safe_name(name)/(safe_name(name)+".glb")).as_posix()
    data["generated_at"]=datetime.now().isoformat(timespec="seconds"); DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8"); (folder/"meta.json").write_text(json.dumps(item,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(item=item)

@app.put("/api/items/batch")
def batch_edit():
    body=request.get_json(silent=True) or {}
    ids=set(body.get("ids") or [])
    tags=[str(x).strip() for x in (body.get("tags") or []) if str(x).strip()]
    weapons=[str(x).strip() for x in (body.get("weapons") or []) if str(x).strip()]
    data=read_data(); items=[x for x in data.get("items",[]) if x.get("id") in ids]
    if not items: return jsonify(error="没有选择动画"),400
    enum_tags=set(data.get("enums",{}).get("tags",[])); enum_weapons=set(data.get("enums",{}).get("weapons",DEFAULT_WEAPONS))
    if any(tag not in enum_tags for tag in tags): return jsonify(error="包含无效标签"),400
    if any(weapon not in enum_weapons for weapon in weapons): return jsonify(error="包含无效武器标签"),400
    for item in items:
        item["tags"]=list(dict.fromkeys([*item.get("tags",[]),*tags]))
        item["weapons"]=list(dict.fromkeys([*item.get("weapons",[]),*weapons]))
        folder=ROOT/Path(item["preview_url"]).parent
        if (folder/"meta.json").exists(): (folder/"meta.json").write_text(json.dumps(item,ensure_ascii=False,indent=1),encoding="utf-8")
    data["generated_at"]=datetime.now().isoformat(timespec="seconds")
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(items=items)

@app.get("/")
def index(): return send_from_directory(ROOT,"index.html")

@app.delete("/api/items/<item_id>")
def delete_item(item_id):
    data=read_data(); item=next((x for x in data.get("items",[]) if x.get("id")==item_id),None)
    if not item: return jsonify(error="找不到动画"),404
    folder=(ROOT/Path(item.get("preview_url","")).parent).resolve()
    assets_root=(ROOT/"assets").resolve()
    if assets_root not in folder.parents: return jsonify(error="资产路径无效"),400
    if folder.exists(): shutil.rmtree(folder)
    data["items"]=[x for x in data.get("items",[]) if x.get("id")!=item_id]; data["generated_at"]=datetime.now().isoformat(timespec="seconds")
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding="utf-8")
    return jsonify(ok=True)

@app.get("/<path:path>")
def files(path): return send_from_directory(ROOT,path)

if __name__=="__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1",port=5000,debug=False)
