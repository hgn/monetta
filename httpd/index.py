from aiohttp import web

async def handle(request):
    return web.Response(text="Hello, world")
