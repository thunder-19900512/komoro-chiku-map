#!/usr/bin/env python3
"""こもろ地区ガイド（公開層）ビルドスクリプト
e-Stat小地域Shape → docs/data.geojson ＋ 地区集計。
⚠️ 公開層: 非公開データ（活動ログ・地区メモ等）をこのリポジトリに置かないこと（憲法1）。
"""
import shapefile, json, os, csv

BASE = os.path.dirname(os.path.abspath(__file__))
SHP = os.path.join(BASE, "data/estat_shape/r2ka20208")
DOCS = os.path.join(BASE, "docs")
os.makedirs(DOCS, exist_ok=True)

# ---- 町丁字 → 10地区 対応表（確度つき。u=要確認） ----------------------
# 根拠: 小諸市行政区マップ(H26) + 各地区の紹介(市公式) + 基礎メモ(Drive)
D = {}
def put(chiku, names, unsure=False):
    for n in names: D[n] = (chiku, unsure)

put("中央（東南部）", ["甲小原","甲東小諸","甲東山","甲緑ヶ丘","乙女",
    "御幸町一丁目","御幸町二丁目","与良町一丁目","与良町二丁目","与良町三丁目",
    "与良町四丁目","与良町五丁目","与良町六丁目","鶴巻一丁目","鶴巻二丁目",
    "赤坂一丁目","赤坂二丁目","南町一丁目","南町二丁目","南町三丁目"])
put("中央（東部）", ["荒町一丁目","荒町二丁目","紺屋町一丁目","紺屋町二丁目","紺屋町三丁目",
    "八幡町一丁目","八幡町二丁目","八幡町三丁目","三和一丁目","三和二丁目","三和三丁目",
    "甲天池","甲松井","松井一丁目","松井二丁目","甲東雲",
    "東雲一丁目","東雲二丁目","東雲三丁目","東雲四丁目","東雲五丁目","東雲六丁目","東雲七丁目"])
put("中央（中部）", ["相生町一丁目","相生町二丁目","相生町三丁目","本町一丁目","本町二丁目","本町三丁目",
    "乙本町","六供一丁目","六供二丁目","乙六供","田町一丁目","田町二丁目","田町三丁目",
    "大手一丁目","大手二丁目"])
put("中央（西部）", ["甲古城","古城一丁目","古城二丁目","古城三丁目","乙古城","丙古城",
    "市町一丁目","市町二丁目","市町三丁目","市町四丁目","市町五丁目",
    "新町一丁目","新町二丁目","丙新町","両神","丙富士見平"])
put("大里", ["大字菱平菱野","大字菱平後平","大字諸","諸","大字西原西原","大字西原滝原","大字滝原"])
put("大里", ["大字菱平六供"], unsure=True)          # 菱平の小字。行政区マップからざっくり大里
put("北大井", ["大字塩野"], unsure=True)            # 凡例の乗瀬区に対応する可能性（他に候補小地域なし）
put("西小諸", ["大字滋野甲芝生田","大字滋野甲井子","大字滋野甲糠地"])
put("西小諸", ["大字滋野甲新町"], unsure=True)
put("北大井", ["大字八満原村","大字八満中村","大字八満八代","大字八満西八満","大字八満東",
    "大字八満藤塚","大字八満南ケ原","大字柏木石峠","大字柏木柏木上","大字柏木柏木下",
    "大字柏木四ツ谷","大字加増石峠","大字加増柏木下","大字加増ひばりケ丘","大字加増加増",
    "加増一丁目","加増二丁目","加増三丁目"])
put("北大井", ["大字柏木東","甲四ッ谷"], unsure=True)
put("川辺", ["大字大久保大久保","大字大久保氷","大字大久保鴇久保","大字大久保御牧ケ原",
    "大字大久保諏訪山","大字山浦西浦","大字山浦上ノ平","大字山浦久保","大字山浦大杭",
    "大字山浦宮沢","大字山浦御牧ケ原"])
put("三岡", ["大字市市","大字市耳取","大字市森山","大字耳取","大字森山"])
put("南大井", ["大字御影新田御影","大字御影新田一ツ谷","大字御影新田谷地原",
    "大字平原平原","大字和田"])
put("南大井", ["大字平原東"], unsure=True)
put("中央（西部）", ["丁"], unsure=True) # 地番区域（懐古園周辺）。行政区マップからざっくり西部
put("大里", ["己"], unsure=True)        # 北部の浅間山麓の広大な地番区域。行政区マップでは西側=菱野区(大里)・東側=天池区(東部)に跨るが、中心が大里側のためざっくり大里

CHIKU_COLORS = {
    "中央（東南部）":"#b48ead","中央（東部）":"#4c9a6a","中央（中部）":"#e0c24e",
    "中央（西部）":"#d1604d","大里":"#4d9dd1","西小諸":"#dd9a4a","北大井":"#8fbf6b",
    "川辺":"#6b7fc7","三岡":"#c7c26b","南大井":"#d98a9e","未確認":"#9aa5a0",
}

# ---- 地区の紹介（出典: 小諸市都市計画マスタープラン 地域別構想 H28改定） ----
# vision=地域の将来像（原文） / desc=地域の特徴 / issue=住民アンケートからの課題
CHIKU_INFO = {
 "中央（東南部）":{
  "vision":"便利な都市環境と豊かな自然が共存する心豊かな魅力あふれるまち",
  "desc":"旧小諸町の東南部。旧北国街道沿いに商業・医療・福祉施設が連なり、周辺に住宅地が広がる。しなの鉄道東小諸駅・乙女駅、南城公園・乙女湖公園など公共施設も多い多様なエリア。",
  "issue":"歩行者の安全性、高齢・障がい者の生活しやすさ。駅周辺整備や「北国街道」を活かしたまちづくり、ヴィオ跡地・厚生病院移転後の跡地利活用が論点。",
  "ku":"小原・東小諸・東山・乙女・御幸町・与良・鶴巻・赤坂・南町・緑ヶ丘"},
 "中央（東部）":{
  "vision":"子ども「すくすく」 若者「いきいき」 高齢者「はつらつ」〜住んでみたい 住みつづけたいまち〜",
  "desc":"市街地から北は高峰高原まで、標高700〜2,000mに細長く伸びる地域。中腹に住宅地、天池の高原野菜・松井の果樹園、チェリーパークラインで高峰高原へ。高地トレーニング拠点構想も。",
  "issue":"満足度は市内で2番目に低く、生活道路・歩行者の安全と、北部高原地域の自然災害への備えが課題。コンパクトシティ形成・空き家バンク活用を掲げる。",
  "ku":"荒町・紺屋町・八幡町・三和・天池・松井・東雲"},
 "中央（中部）":{
  "vision":"人と人が出会い、集い、交わり、賑わうまち／歴史・文化を守り、伝え、きずなを育むまち",
  "desc":"小諸駅・市役所・図書館・商店街が集まる中心市街地。北国街道・大手門・島崎藤村ゆかりの旧跡など歴史資産と共存。集約都市開発（コンパクトシティ）事業が進行。",
  "issue":"安全・安心、道路・交通の重要度が高い。空き家・空き店舗の活用、駐車場整備、懐古園から街なかへ人が流れる回遊の仕組みづくりが論点。",
  "ku":"相生・本町・六供・田町・大手"},
 "中央（西部）":{
  "vision":"世代を超え 歴史や文化を繋ぎ、支え合う、詩情豊かなまち",
  "desc":"懐古園（小諸城址）を擁する市の顔。本陣問屋場・脇本陣など旧北国街道の歴史資産が集積し、観光施設も点在。両神・富士見平・押出は住宅地。",
  "issue":"まちづくり満足度は全10地域で唯一プラス＆最高（景観・公園緑地の評価が高い）。支え合いマップ・自主防災組織づくり、空き家の維持管理、「地区のお宝」の周知活用を掲げる。",
  "ku":"古城・市町・新町・両神・富士見平"},
 "大里":{
  "vision":"大里地区は、学びと交流の郷づくり〜地域全体が「大里劇場」「大里博物館」「大里学校」〜",
  "desc":"市の北西部、上信越道小諸ICを擁する玄関口。浅間サンライン沿いに田園、棚田百選の地区も。マンズワイン工場・菱野温泉・高原美術館・ゴルフ場など交流拠点が多い。",
  "issue":"重要度が全地域で最高（1.049）＝期待が大きい。ICのポテンシャルを活かした6次産業拠点・着地型観光・インター小諸工業団地への企業誘致、通学路の安全確保を掲げる。",
  "ku":"菱野・後平・諸・西原・滝原"},
 "西小諸":{
  "vision":"素晴らしい自然景観・田園風景が残り、地域の人と人とがつながり合う、笑顔あふれる地域",
  "desc":"市の西部、東御市に隣接。糠地は昭和から続く民宿村で、深沢渓谷・みはらし交流館などグリーンツーリズム拠点が点在。棚田と田園風景。",
  "issue":"満足度は3番目に低い。3区を繋ぐ南北幹線の検討、蕎麦・ワイン用葡萄・胡桃のブランド化と6次産業化、3区共同のコミュニティセンター建設を掲げる。",
  "ku":"芝生田・井子・糠地"},
 "北大井":{
  "vision":"15区のつながりは、人と地域のふれ合い・支え合い、みんなで輝く北大井〜浅間のふもと、高原野菜と豊かな自然や伝統文化が織りなす、心かよう郷〜",
  "desc":"市の東部、御代田町に隣接。全10地域で最多の15区。地区の代名詞・高原野菜地帯が広がり、グリーンロード周辺は日当たりと交通利便で新築住宅・店舗が増加中。",
  "issue":"歩行者の安全、バスの利用しやすさ、子どもの遊び場。見どころマップでの魅力発信、「農」を活かした移住定住（Iターン・Uターン）促進、集会施設の耐震化を掲げる。",
  "ku":"原村・中村・八代・西八満・東・藤塚・石峠・柏木上・柏木下・四ツ谷・加増・荒堀・南ケ原・乗瀬・ひばりケ丘"},
 "川辺":{
  "vision":"子どもたちの笑顔が輝き、暮らす人々の笑い声が響く郷",
  "desc":"千曲川西岸〜御牧ヶ原台地。布引観音、農業大学校、あぐりの湯、いちご園など拠点が点在。御牧ヶ原の粘土地を活かした米・白土馬鈴薯はブランド化。田園景観の美しさに定評。千曲小学校の地区。",
  "issue":"満足度が全地域で最低（-0.385）。医療・福祉施設への行きやすさ、避難場所の分かりやすさ、土砂災害対策。「儲かる農業」・企業誘致・移住定住による人口減少への歯止めを掲げる。",
  "ku":"大久保・氷・鴇久保・西浦・上ノ平・久保・大杭・宮沢・御牧ヶ原・諏訪山"},
 "三岡":{
  "vision":"人の交流が促進するまち〜子どもからお年寄りまでが、安全で安心して暮らせる地域〜",
  "desc":"市の南部、佐久市に隣接する平坦な地域。JR小海線の三岡駅・美里駅。桃やリンゴの果樹栽培が盛んで果樹園・直売所が多い。佐久平駅に近く宅地開発が進み人口は増加傾向。",
  "issue":"道路の通行しやすさ、歩行者の安全、身近な子どもの遊び場。佐久市のベッドタウンとしての定住人口増、蛍が生息できる池の復活、美里保育園の休日園庭解放などを掲げる。",
  "ku":"市・耳取・森山"},
 "南大井":{
  "vision":"農業・工業・商業がバランスよく成長し、人々でにぎわうまち",
  "desc":"市の東部、佐久市・御代田町に隣接。国道141号沿いは大型商業施設・住宅開発が急速に進み、和田工業団地に工場が集積。市内で最も人口が増加。しなの鉄道平原駅、佐久北ICに接続。",
  "issue":"歩行者の安全、避難場所の分かりやすさ、子どもの遊び場。公園・児童館の整備、病児・病後児保育の充実、若者中心の地域コミュニティ形成を掲げる。",
  "ku":"平原・一ツ谷・御影・谷地原・和田"},
}

# ---- 年齢構成（e-Stat 第3表 男女,年齢(5歳階級)別人口 町丁・字等 / 長野県） ----
# 出典: 令和2年国勢調査 小地域集計 statInfId=000032163380（総数行のみ使用）
def load_age():
    import csv as _csv
    path = os.path.join(BASE, "data/nagano_age.csv")
    if not os.path.exists(path): return {}
    rows = list(_csv.reader(open(path, encoding="cp932", errors="replace")))
    header = next(r for r in rows if "町丁字コード" in r)
    def col(name): return header.index(name)
    c_sex, c_city, c_cho = col("男女"), col("市区町村コード"), col("町丁字コード")
    # 3区分は再掲列をそのまま使う（5歳刻みの自前合算より確実）
    c_u15, c_1564, c_65 = col("（再掲）15歳未満"), col("（再掲）15～64歳"), col("（再掲）65歳以上")
    def num(v):
        try: return int(str(v).replace(",",""))
        except: return 0
    out = {}
    for r in rows:
        if len(r) <= c_65 or r[c_sex] != "総数" or r[c_city] != "20208": continue
        cho = r[c_cho].strip()
        if cho in ("", "-"): continue
        key = "20208" + cho
        out[key] = (num(r[c_u15]), num(r[c_1564]), num(r[c_65]))
    return out

AGE = load_age()

sf = shapefile.Reader(SHP, encoding="cp932")
fields = [f[0] for f in sf.fields[1:]]
i_name, i_j, i_s = fields.index("S_NAME"), fields.index("JINKO"), fields.index("SETAI")
i_key = fields.index("KEY_CODE")

feats, agg, review = [], {}, []
age_hit = 0
for srec in sf.iterShapeRecords():
    name = srec.record[i_name]
    jinko, setai = int(srec.record[i_j] or 0), int(srec.record[i_s] or 0)
    key = str(srec.record[i_key])
    chiku, unsure = D.get(name, ("未確認", True))
    if unsure: review.append([name, chiku, jinko])
    g = srec.shape.__geo_interface__
    a0, a15, a65 = AGE.get(key, (None, None, None))
    if a0 is not None: age_hit += 1
    props = {"name":name,"chiku":chiku,"jinko":jinko,"setai":setai,
        "color":CHIKU_COLORS[chiku],"unsure":unsure}
    if a0 is not None:
        tot3 = a0 + a15 + a65
        props.update({"a0":a0,"a15":a15,"a65":a65,
            "kourei": round(a65/tot3*100,1) if tot3 else None})
    feats.append({"type":"Feature","geometry":g,"properties":props})
    a = agg.setdefault(chiku, {"jinko":0,"setai":0,"n":0,"a0":0,"a15":0,"a65":0})
    a["jinko"] += jinko; a["setai"] += setai; a["n"] += 1
    if a0 is not None:
        a["a0"] += a0; a["a15"] += a15; a["a65"] += a65

with open(os.path.join(DOCS,"data.geojson"),"w") as f:
    json.dump({"type":"FeatureCollection","features":feats}, f, ensure_ascii=False)

info = {}
for c, a in agg.items():
    base = CHIKU_INFO.get(c, {"desc":"（対応表が未確認の小地域）","ku":"—"})
    tot3 = a["a0"] + a["a15"] + a["a65"]
    if tot3:
        a["kourei"] = round(a["a65"]/tot3*100,1)
        a["nensyo"] = round(a["a0"]/tot3*100,1)
    info[c] = {**base, **a, "color":CHIKU_COLORS[c]}
with open(os.path.join(DOCS,"chiku_info.json"),"w") as f:
    json.dump(info, f, ensure_ascii=False, indent=1)

with open(os.path.join(BASE,"data/対応表_要確認リスト.csv"),"w") as f:
    w = csv.writer(f); w.writerow(["小地域名","仮の地区","人口"]); w.writerows(review)

# ---- 人流データ（国交省 全国の人流オープンデータ 1kmメッシュ 2021-12） -----
# 出典: G空間情報センター mlit-1km-fromto（政府標準利用規約）。dayflag 0=休日/1=平日, timezone 0=昼/1=深夜
JINRYU_CSV = os.path.join(BASE, "data/jinryu_nagano/20/2021/12/monthly_mdp_mesh1km.csv")
if os.path.exists(JINRYU_CSV):
    def mesh_poly(code):  # 標準地域メッシュ(3次・1km)コード8桁 → ポリゴン
        ab, cd = int(code[0:2]), int(code[2:4])
        e, f_, g, h = int(code[4]), int(code[5]), int(code[6]), int(code[7])
        lat0 = ab / 1.5 + e * (1/12) + g * (1/120)
        lon0 = 100 + cd + f_ * (1/8) + h * (1/80)
        la, lo = 1/120, 1/80
        return [[[lon0, lat0], [lon0+lo, lat0], [lon0+lo, lat0+la], [lon0, lat0+la], [lon0, lat0]]]
    mesh = {}
    with open(JINRYU_CSV) as f:
        for r in csv.DictReader(f):
            if r["citycode"] != "20208": continue
            key = {"1":{"0":"wd","1":"wn"},"0":{"0":"hd","1":"hn"}}.get(r["dayflag"],{}).get(r["timezone"])
            if not key: continue  # 全日・終日は使わない
            mesh.setdefault(r["mesh1kmid"], {})[key] = int(r["population"])
    jfeats = [{"type":"Feature","geometry":{"type":"Polygon","coordinates":mesh_poly(m)},
               "properties":{"mesh":m, **{k: v.get(k) for k in ("wd","wn","hd","hn")}}}
              for m, v in mesh.items()]
    with open(os.path.join(DOCS,"jinryu.geojson"),"w") as f:
        json.dump({"type":"FeatureCollection","features":jfeats}, f, ensure_ascii=False)
    print(f"人流: {len(jfeats)}メッシュ → docs/jinryu.geojson（2021年12月・平日/休日×昼/深夜）")

# ---- ポスター掲示場（R7参院選・選管公示ベース） --------------------------
# ⚠️ 公開版には number/address/座標のみ出力。name列（個人宅名を含む）は公開しない。
pcsv = os.path.join(BASE, "data/posters_r7sangiin.csv")
if os.path.exists(pcsv):
    pfeats = []
    with open(pcsv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try: lat, lng = float(r["lat"]), float(r["long"])
            except: continue
            pfeats.append({"type":"Feature",
                "geometry":{"type":"Point","coordinates":[lng, lat]},
                "properties":{"no":r["number"].strip(),"addr":r["address"].strip()}})
    with open(os.path.join(DOCS,"posters.geojson"),"w") as f:
        json.dump({"type":"FeatureCollection","features":pfeats}, f, ensure_ascii=False)
    print(f"ポスター掲示場: {len(pfeats)}件 → docs/posters.geojson（name列は非公開）")

print(f"OK: {len(feats)}小地域 → docs/data.geojson（年齢データ結合: {age_hit}/{len(feats)}）")
for c,a in sorted(agg.items(), key=lambda x:-x[1]['jinko']):
    k = f" 高齢化率{a.get('kourei','?')}% 年少{a.get('nensyo','?')}%" if a.get('kourei') else ""
    print(f"  {c}: 人口{a['jinko']:,} 世帯{a['setai']:,} ({a['n']}小地域){k}")
print(f"要確認: {len(review)}件 → data/対応表_要確認リスト.csv")
