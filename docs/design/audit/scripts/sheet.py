import os, glob
from PIL import Image, ImageDraw, ImageFont
ROOT="/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit/shots"
CELL_W, MAXH, PAD, LABEL = 380, 900, 14, 22
try: F=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf",13)
except: F=ImageFont.load_default()

for surface in sorted(os.listdir(ROOT)):
    d=os.path.join(ROOT,surface)
    if not os.path.isdir(d) or surface=='focus': continue
    tiles=[]
    for vp in ['375x812','768x1024','1440x900']:
        for p in sorted(glob.glob(os.path.join(d,vp,'*.png'))):
            tiles.append((f"{vp} · {os.path.basename(p)[:-4]}", p))
    if not tiles: continue
    imgs=[]
    for label,p in tiles:
        im=Image.open(p).convert('RGB')
        w,h=im.size
        nh=int(h*CELL_W/w)
        if nh>MAXH:  # crop tall pages to the top, note it in the label
            im=im.crop((0,0,w,int(w*MAXH/CELL_W))); label+=" (top)"
            nh=MAXH
        imgs.append((label, im.resize((CELL_W,nh), Image.LANCZOS)))
    cols=min(5,len(imgs))
    rows=(len(imgs)+cols-1)//cols
    rowh=[]
    for r in range(rows):
        rowh.append(max(im.size[1] for _,im in imgs[r*cols:(r+1)*cols])+LABEL+PAD)
    W=cols*(CELL_W+PAD)+PAD
    H=sum(rowh)+PAD
    sheet=Image.new('RGB',(W,H),(249,245,242))
    dr=ImageDraw.Draw(sheet)
    y=PAD
    for r in range(rows):
        x=PAD
        for label,im in imgs[r*cols:(r+1)*cols]:
            dr.text((x,y),label[:56],fill=(23,23,23),font=F)
            sheet.paste(im,(x,y+LABEL))
            dr.rectangle([x,y+LABEL,x+CELL_W,y+LABEL+im.size[1]],outline=(180,175,168))
            x+=CELL_W+PAD
        y+=rowh[r]
    out=os.path.join(ROOT,f"_contact-sheet-{surface}.png")
    sheet.save(out, optimize=True)
    print(f"{surface}: {len(imgs)} tiles -> {out} ({sheet.size[0]}x{sheet.size[1]}, {os.path.getsize(out)//1024} KB)")
