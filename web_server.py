from aiohttp import web
import os


async def handle_map(request):
    if os.path.exists("map.html"):
        with open("map.html", "r") as f:
            return web.Response(text=f.read(), content_type="text/html")
    return web.Response(text="Карта пока не создана", content_type="text/html")


def create_app():
    app = web.Application()
    app.router.add_get("/", handle_map)
    return app