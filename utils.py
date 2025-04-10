import httpx

class NoEncodeTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request):
        request.url = httpx.URL(str(request.url).replace('%22', '"'))
        request.url = httpx.URL(str(request.url).replace('%25', '%'))
        return await super().handle_async_request(request)