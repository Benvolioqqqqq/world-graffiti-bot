import folium
from folium.plugins import MarkerCluster
import base64
import os
from io import BytesIO
from PIL import Image
from aiogram import Bot
from database import get_all_graffiti, get_all_reactions

def compress_photo(photo_path, max_width=300, quality=40):
    img = Image.open(photo_path)
    ratio = max_width / img.width
    new_height = int(img.height * ratio)
    img = img.resize((max_width, new_height), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode()


def get_marker_icon_base64():
    img = Image.open("marker.png")
    img = img.resize((72, 72), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode()


def make_popup_html(img_base64, author, date, description, reactions=None):
    if reactions is None:
        reactions = {"fire": 0, "like": 0, "puke": 0}

    img_section = ""
    if img_base64:
        img_section = f'''
            <div style="width:100%; border-radius:10px; overflow:hidden; margin-bottom:10px;">
                <img src="data:image/jpeg;base64,{img_base64}" 
                     style="width:100%; display:block;">
            </div>
        '''

        parts = [
            f'🔥 {reactions["fire"]}',
            f'👍 {reactions["like"]}',
            f'🤮 {reactions["puke"]}'
        ]
        reaction_html = f'''
            <div style="
                font-size:13px;
                color:#666;
                border-top:1px solid #eee;
                padding-top:6px;
                margin-top:6px;
            ">{" &nbsp; ".join(parts)}</div>
        '''

    return f'''
    <div style="
        width:240px; 
        font-family:'Segoe UI', Arial, sans-serif; 
        padding:0; 
        margin:0;
        line-height:1.4;
    ">
        {img_section}
        <div style="padding:2px 4px;">
            <div style="
                font-size:14px; 
                font-weight:bold; 
                color:#6C3483; 
                margin-bottom:6px;
            ">🎨 {author}</div>
            <div style="
                font-size:12px; 
                color:#666; 
                margin-bottom:4px;
            ">📅 {date}</div>
            <div style="
                font-size:12px; 
                color:#333;
                border-top:1px solid #eee;
                padding-top:6px;
                margin-top:4px;
            ">{description or '<i style="color:#999;">No description</i>'}</div>
            {reaction_html}
        </div>
    </div>
    '''


def get_all_users():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

async def generate_map(bot: Bot):
    world_map = folium.Map(
        location=[20, 0],
        zoom_start=3,
        tiles="OpenStreetMap"
    )

    marker_cluster = MarkerCluster(
        name="Граффити",
        options={
            "maxClusterRadius": 20,
            "disableClusteringAtZoom": 13,
            "minimumClusterSize": 10
        }
    ).add_to(world_map)

    # Загружаем иконку один раз
    icon_base64 = get_marker_icon_base64()
    all_reactions = get_all_reactions()

    # Добавляем CSS-стиль с иконкой один раз в карту
    icon_css = f'''
    <style>
        .graffiti-icon {{
            width: 36px;
            height: 36px;
            background-image: url('data:image/png;base64,{icon_base64}');
            background-size: contain;
            background-repeat: no-repeat;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
        }}
    </style>
    '''
    world_map.get_root().html.add_child(folium.Element(icon_css))

    graffiti_list = get_all_graffiti()
    os.makedirs("photos", exist_ok=True)

    for item in graffiti_list:
        g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status, city = item

        img_base64 = ""
        if photo_id:
            photo_path = f"photos/{g_id}.jpg"
            file = await bot.get_file(photo_id)
            await bot.download_file(file.file_path, photo_path)
            img_base64 = compress_photo(photo_path)

        reactions = all_reactions.get(g_id, {"fire": 0, "like": 0, "puke": 0})
        popup_html = make_popup_html(img_base64, author, date, description, reactions)

        icon = folium.DivIcon(
            html='<div class="graffiti-icon"></div>',
            icon_size=(36, 36),
            icon_anchor=(18, 36),
            popup_anchor=(0, -36)
        )

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=260),
            icon=icon
        ).add_to(marker_cluster)

    world_map.save("map.html")