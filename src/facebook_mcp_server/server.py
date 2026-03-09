import asyncio
import os
import sys
import logging
import requests
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl
from typing import Any
from dotenv import load_dotenv


# Load environment variables from .env file (cwd first, then project root / parent dir)
load_dotenv()
# When run from facebook-mcp-server (e.g. OpenClaw), cwd may not contain .env; also check parent dirs
_server_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_server_dir))  # facebook-mcp-server
_parent_dir = os.path.dirname(_project_root)  # parent of facebook-mcp-server (monorepo root)
for _path in (os.path.join(_parent_dir, ".env"), os.path.join(_project_root, ".env")):
    if os.path.isfile(_path):
        load_dotenv(_path)  # later load wins for unset vars; dotenv doesn't override already-set

# Reconfigure UnicodeEncodeError prone default (i.e. windows-1252) to utf-8
if sys.platform == "win32" and os.environ.get('PYTHONIOENCODING') is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger('facebook_mcp_server')
logger.info("Starting Facebook MCP Server")

# Page access token and Page ID (required for new Pages experience).
# Must be a PAGE token (from /me/accounts or Page token in Access Token Tool), not a User token.
PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID")


def _require_page_credentials() -> None:
    """Raise a clear error if Page token or ID is missing (avoids opaque Facebook OAuth errors)."""
    if not PAGE_ACCESS_TOKEN or not PAGE_ACCESS_TOKEN.strip():
        raise ValueError(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not set or empty. "
            "Set it to a Page access token (not a User token). "
            "Get one via Graph API: GET /me/accounts with a User token, or from Meta App Dashboard → Tools → Access Token Tool (select your Page)."
        )
    if not PAGE_ID or not PAGE_ID.strip():
        raise ValueError(
            "FACEBOOK_PAGE_ID is not set or empty. "
            "Set it to your Facebook Page ID (e.g. 1078511068671402)."
        )

# Facebook Graph API endpoint
GRAPH_API_VERSION = "v18.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

class FacebookManager:
    def post_to_facebook(self, message: str) -> dict[str, Any]:
        """Posts a message to the Facebook Page. Requires a Page access token."""
        _require_page_credentials()
        url = f"{GRAPH_API_BASE_URL}/{PAGE_ID}/feed"
        params = {
            "message": message,
            "access_token": PAGE_ACCESS_TOKEN,
        }
        response = requests.post(url, params=params)
        return response.json()

    def reply_to_comment(self, post_id: str, comment_id: str, message: str) -> dict[str, Any]:
        """Replies to a comment on a specific post. Requires a Page access token."""
        _require_page_credentials()
        url = f"{GRAPH_API_BASE_URL}/{comment_id}/comments"
        params = {
            "message": message,
            "access_token": PAGE_ACCESS_TOKEN,
        }
        response = requests.post(url, params=params)
        return response.json()

    def get_page_posts(self) -> dict[str, Any]:
        """Retrieves posts published on the Facebook Page. Requires a Page access token (new Pages experience)."""
        _require_page_credentials()
        url = f"{GRAPH_API_BASE_URL}/{PAGE_ID}/posts"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "id,message,created_time",
        }
        response = requests.get(url, params=params)
        return response.json()

    def get_post_comments(self, post_id: str) -> dict[str, Any]:
        """Retrieves comments for a specific post. Requires a Page access token."""
        _require_page_credentials()
        url = f"{GRAPH_API_BASE_URL}/{post_id}/comments"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
            "fields": "id,message,from,created_time",
        }
        response = requests.get(url, params=params)
        return response.json()

    def filter_negative_comments(self, comments: dict[str, Any]) -> list[dict[str, Any]]:
        """Filters negative comments based on a simple keyword list."""
        negative_keywords = ["bad", "terrible", "awful", "hate", "dislike", "problem", "issue"]
        negative_comments = []
        if 'data' in comments:
            for comment in comments['data']:
                if 'message' in comment:
                    for keyword in negative_keywords:
                        if keyword in comment['message'].lower():
                            negative_comments.append(comment)
                            break
        return negative_comments
    
    def delete_post(self, post_id: str) -> dict[str, Any]:
        """Deletes a post from the Facebook Page. Requires a Page access token."""
        _require_page_credentials()
        url = f"{GRAPH_API_BASE_URL}/{post_id}"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
        }
        response = requests.delete(url, params=params)
        return response.json()

    def delete_comment(self, comment_id: str) -> dict[str, Any]:
        """Deletes a comment from a post. Requires a Page access token."""
        _require_page_credentials()
        url = f"{GRAPH_API_BASE_URL}/{comment_id}"
        params = {
            "access_token": PAGE_ACCESS_TOKEN,
        }
        response = requests.delete(url, params=params)
        return response.json()

    def debug_token(self) -> dict[str, Any]:
        """Calls Facebook Debug Token API on FACEBOOK_PAGE_ACCESS_TOKEN. Use to verify token type (PAGE vs USER) and that env is passed correctly."""
        token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or ""
        page_id_env = os.environ.get("FACEBOOK_PAGE_ID") or ""
        out: dict[str, Any] = {
            "env_check": {
                "FACEBOOK_PAGE_ACCESS_TOKEN_set": bool(token.strip()),
                "FACEBOOK_PAGE_ACCESS_TOKEN_length": len(token),
                "FACEBOOK_PAGE_ACCESS_TOKEN_prefix": (token[:20] + "...") if len(token) > 20 else token,
                "FACEBOOK_PAGE_ID": page_id_env or "(empty)",
            },
        }
        if not token.strip():
            out["debug_token_response"] = None
            out["summary"] = "ERROR: FACEBOOK_PAGE_ACCESS_TOKEN is empty; env may not be passed to the server."
            return out
        url = f"{GRAPH_API_BASE_URL}/debug_token"
        params = {
            "input_token": token,
            "access_token": token,
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
            out["debug_token_response"] = data
            if "data" in data:
                d = data["data"]
                token_type = d.get("type", "?")
                is_valid = d.get("is_valid", False)
                profile_id = d.get("profile_id", "")
                out["summary"] = (
                    f"Token type={token_type!r}, valid={is_valid}, profile_id={profile_id!r}. "
                    f"Configured FACEBOOK_PAGE_ID={page_id_env!r}. "
                )
                if token_type != "PAGE":
                    out["summary"] += "This token is NOT a Page token; get_page_posts will fail. Use a Page token from Access Token Tool or from GET /me/accounts."
                elif str(profile_id) != str(page_id_env):
                    out["summary"] += f"WARNING: Token profile_id ({profile_id}) does not match FACEBOOK_PAGE_ID ({page_id_env})."
            else:
                out["summary"] = f"Debug API returned no 'data'; check 'debug_token_response' for errors: {data}"
        except Exception as e:
            out["debug_token_response"] = None
            out["summary"] = f"Exception calling debug_token: {e}"
        return out

async def main():
    logger.info("Starting Facebook MCP Server")

    fb_manager = FacebookManager()
    server = Server("facebook-manager")

    # Register handlers
    logger.debug("Registering handlers")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="post_to_facebook",
                description="Posts a message to the Facebook Page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to post"},
                    },
                    "required": ["message"],
                },
            ),
            types.Tool(
                name="reply_to_comment",
                description="Replies to a comment on a specific post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string", "description": "ID of the post"},
                        "comment_id": {"type": "string", "description": "ID of the comment"},
                        "message": {"type": "string", "description": "Reply message"},
                    },
                    "required": ["post_id", "comment_id", "message"],
                },
            ),
            types.Tool(
                name="get_page_posts",
                description="Retrieves posts published on the Facebook Page",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_post_comments",
                description="Retrieves comments for a specific post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string", "description": "ID of the post"},
                    },
                    "required": ["post_id"],
                },
            ),
            types.Tool(
                name="filter_negative_comments",
                description="Filters negative comments from a post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string", "description": "ID of the post"},
                    },
                    "required": ["post_id"],
                },
            ),
            types.Tool(
                name="delete_post",
                description="Deletes a post from the Facebook Page.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string", "description": "ID of the post to delete."},
                    },
                    "required": ["post_id"],
                },
            ),
            types.Tool(
                name="delete_comment",
                description="Deletes a comment from a post.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "comment_id": {"type": "string", "description": "ID of the comment to delete."},
                    },
                    "required": ["comment_id"],
                },
            ),
            types.Tool(
                name="debug_token",
                description="Debug the current FACEBOOK_PAGE_ACCESS_TOKEN: shows env check and Facebook token type (PAGE vs USER). Use when get_page_posts fails with 'User access token is not supported'.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            if name == "post_to_facebook":
                result = fb_manager.post_to_facebook(arguments["message"])
                return [types.TextContent(type="text", text=str(result))]
            elif name == "reply_to_comment":
                result = fb_manager.reply_to_comment(arguments["post_id"], arguments["comment_id"], arguments["message"])
                return [types.TextContent(type="text", text=str(result))]
            elif name == "get_page_posts":
                result = fb_manager.get_page_posts()
                return [types.TextContent(type="text", text=str(result))]
            elif name == "get_post_comments":
                result = fb_manager.get_post_comments(arguments["post_id"])
                return [types.TextContent(type="text", text=str(result))]
            elif name == "filter_negative_comments":
                comments = fb_manager.get_post_comments(arguments["post_id"])
                result = fb_manager.filter_negative_comments(comments)
                return [types.TextContent(type="text", text=str(result))]
            elif name == "delete_post":
                result = fb_manager.delete_post(arguments["post_id"])
                return [types.TextContent(type="text", text=str(result))]
            elif name == "delete_comment":
                result = fb_manager.delete_comment(arguments["comment_id"])
                return [types.TextContent(type="text", text=str(result))]
            elif name == "debug_token":
                result = fb_manager.debug_token()
                return [types.TextContent(type="text", text=str(result))]
            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="facebook",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
