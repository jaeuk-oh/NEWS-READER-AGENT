import os, re
from crewai.tools import tool
from firecrawl import FirecrawlApp, ScrapeOptions

#@tool
def web_search_tool(query: str):
    """
    Web Search Tool.
    Args:
        query: str
            The query to search the web for.
    Returns
        A list of search result with the website content in Markdown format.
    """
    app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

    print(f"Searching for {query}")

    response = app.search(
        query=query,
        limit=1,
        scrape_options=ScrapeOptions(
            formats=["markdown"]
        )
    )
    # response -> keys(['title', 'description', 'url', 'markdown', 'metadata'])

    if not response.success:
        return "Error using tools"

    # 모델 입력에 불필요한 특수 토큰(\n, ** 등)이 다수 포함되어 있어, 정규화 목적의 텍스트 전처리를 수행
    cleaned_chunks = []

    for result in response.data:
        # data = [{'title':'1','desc':'2','url':'3'}, {...}, {..}, ...]
        # result = {'title':'1','desc':'2','url':'3'}
        title = result['title']
        url = result['url']
        markdown = result['markdown']

        # \\+ : 백슬래시 2개 이상 , \n+ : 줄바꿈 2개 이상, strip은 양쪽 끝 공백 제거
        cleaned_1 = re.sub(r"\\+|\n+", "", markdown).strip() 

        # 필터링 하고자 하는 것 = [링크텍스트](https://example.com) 와 https://example.com 일반 url 둘 다.
        cleaned = re.sub(r"\[[^\]]+\]\([^\)]+\)|https?://[^\s]+", "", cleaned_1)
        # [^\]]+
        # [...] -> 문자 하나, ^\] -> ]를 제외한 문자, + 하나 이상 
        # \s -> 공백

        cleaned_result = {
            "title": title,
            "url": url,
            "markdown": cleaned
        }

        cleaned_chunks.append(cleaned_result)
    
    return cleaned_chunks

a = web_search_tool("what should people do in the AI era")

print(a)