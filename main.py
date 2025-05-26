from fastmcp import FastMCP
import tools.crawler as bc
import tools.keyward as keyward
import os
import json

mcp = FastMCP(
    name="ClimateChangeEvidenceFinder",
    instructions="""
    This MCP Server is designed to find available text on various websites as a basis for questions related to climate change.

    There are two main tools available.
    1. extract : When you specify a URL, it returns a paragraph to JSON for the keyword specified by that URL.
    2. find : When you specify the category and keyword of the question, it searches with that keyword and returns the title and link of the related article to JSON.
    """
)

@mcp.resource("resource://category")
def get_category() -> str:
    """Kinds of categories that can be used in this MCP Server on the tool<find>"""
    sites_file_path = os.path.join(os.path.dirname(__file__), 'tools', 'sites.json')
    with open(sites_file_path, 'r', encoding='utf-8') as f:
        sites_data = json.load(f)
    return sites_data.keys()

mcp.add_tool(keyward.extract_keyword,
             name="extract",
             description="If you give a URL and single keyword as a parameter, it returns the paragraph where the keyword exists to JSON.",
             )

mcp.add_tool(bc.crawl_category,
             name="find",
             description="Search the website with the multiple keywords(space-separated) received as a parameter, and return the title of the article and its link to JSON.",
             )

if __name__ == "__main__":
    mcp.run()