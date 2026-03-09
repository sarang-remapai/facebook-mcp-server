# Facebook MCP Server
<img src="https://badge.mcpx.dev?type=server" title="MCP Server"/>

## Overview

A Model Context Protocol (MCP) server implementation that provides Facebook Page interaction and management capabilities. This server enables automated posting, comment moderation, and content retrieval.

## Components

## Tools

The server offers the following tools:

* **post_to_facebook:**
    * Posts a message to the Facebook Page.
    * Input: `message` (string): The message to post.
* **reply_to_comment:**
    * Replies to a comment on a specific post.
    * Input:
        * `post_id` (string): The ID of the post.
        * `comment_id` (string): The ID of the comment.
        * `message` (string): The reply message.
* **get_page_posts:**
    * Retrieves posts published on the Facebook Page.
    * Input: None.
* **get_post_comments:**
    * Retrieves comments for a specific post.
    * Input: `post_id` (string): The ID of the post.
* **filter_negative_comments:**
    * Filters negative comments from a post based on keywords.
    * Input: `post_id` (string): The ID of the post.
* **delete_post:**
    * Deletes a post from the Facebook Page.
    * Input: `post_id` (string): The ID of the post to delete.
* **delete_comment:**
    * Deletes a comment from a post.
    * Input: `comment_id` (string): The ID of the comment to delete.

## Setup

1.  **Configure Facebook Credentials:**
    * Create a `.env` file in the root directory of your project.
    * Add your Facebook Page access token and Page ID to the `.env` file:

        ```
        FACEBOOK_PAGE_ACCESS_TOKEN=YOUR_PAGE_ACCESS_TOKEN
        FACEBOOK_PAGE_ID=YOUR_PAGE_ID
        ```

    * Replace `YOUR_PAGE_ACCESS_TOKEN` and `YOUR_PAGE_ID` with your actual values.
    * **Important:** Add `.env` to your `.gitignore` to avoid committing sensitive information.

2.  **Configure in Claude Desktop (or your MCP Client):**
    * Configure your MCP client (e.g., Claude Desktop) to connect to the Facebook MCP server.
    * Example configuration for Claude Desktop (uv):

        ```json
        {
          "mcpServers": {
              "facebook": {
                  "command": "uv",
                  "args": [
                      "--directory",
                      "/path/to/facebook-mcp-server",
                      "run",
                      "facebook-mcp-server"  
                  ]
              }
          }
        }
        ```


## Building

Comming Next.


## License

This MCP server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
