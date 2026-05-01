"""
Notion service for creating Application Guide pages.
"""

from typing import Optional, Tuple

from notion_client import Client
from notion_client.errors import APIResponseError

from backend.config import get_settings
from backend.models import ApplicationGuide, CodeSnippetType
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class NotionService:
    """Service for interacting with Notion API."""
    
    def __init__(self):
        """Initialize Notion client."""
        if not settings.notion_api_key:
            raise ValueError(
                "Notion API key is not configured. Set notion_api_key, notion_api, or notion_token."
            )
        self.client = Client(auth=settings.notion_api_key)

    def _get_database_properties(self, database_id: str) -> dict:
        """Fetch the property schema for a Notion database."""
        database = self.client.databases.retrieve(database_id=database_id)
        return database.get("properties", {})

    def _build_status_property_value(self, database_properties: dict) -> Optional[dict]:
        """
        Build a Status property payload that matches the database schema.

        Supports both legacy `select` properties and Notion's newer `status` type.
        """
        status_property = database_properties.get("Status")
        if not status_property:
            return None

        property_type = status_property.get("type")
        preferred_names = ("New", "Not started", "Todo", "To do", "Backlog")

        if property_type == "status":
            options = status_property.get("status", {}).get("options", [])
            selected_name = next(
                (option.get("name") for option in options if option.get("name") in preferred_names),
                None,
            )
            if not selected_name and options:
                selected_name = options[0].get("name")
            return {"status": {"name": selected_name or "Not started"}}

        if property_type == "select":
            options = status_property.get("select", {}).get("options", [])
            selected_name = next(
                (option.get("name") for option in options if option.get("name") in preferred_names),
                None,
            )
            return {"select": {"name": selected_name or "New"}}

        logger.warning("Unsupported Status property type '%s'; skipping status value.", property_type)
        return None
    
    def setup_database(
        self,
        database_name: str = "Application Guides",
        parent_page_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create or get the Application Guides database.
        
        Args:
            database_name: Name for the database
            parent_page_id: Parent page ID (optional)
            
        Returns:
            Tuple of (database_id, database_url)
        """
        # If we have a database ID configured, verify it exists
        if settings.notion_database_id:
            try:
                db = self.client.databases.retrieve(settings.notion_database_id)
                db_url = f"https://notion.so/{settings.notion_database_id.replace('-', '')}"
                return settings.notion_database_id, db_url
            except APIResponseError:
                logger.warning("Configured database ID not found, will create new")
        
        # Search for existing database with this name
        try:
            response = self.client.search(
                query=database_name,
                filter={"property": "object", "value": "database"}
            )
            
            for result in response.get('results', []):
                if result.get('object') == 'database':
                    title_props = result.get('title', [])
                    if title_props and title_props[0].get('plain_text') == database_name:
                        db_id = result['id']
                        db_url = result.get('url', f"https://notion.so/{db_id.replace('-', '')}")
                        logger.info(f"Found existing database: {database_name}")
                        return db_id, db_url
        except Exception as e:
            logger.warning(f"Search failed: {e}")
        
        # Create new database
        if not parent_page_id:
            # Get a page to use as parent
            try:
                response = self.client.search(
                    filter={"property": "object", "value": "page"},
                    page_size=1
                )
                if response.get('results'):
                    parent_page_id = response['results'][0]['id']
            except Exception as e:
                logger.error(f"Could not find parent page: {e}")
                raise ValueError(
                    "No parent page found. Please create a page in Notion and share it with the integration, "
                    "or provide a parent_page_id."
                )
        
        # Create database with required properties
        db_properties = {
            "Title": {"title": {}},
            "Channel": {"rich_text": {}},
            "Video URL": {"url": {}},
            "Views": {"number": {"format": "number_with_commas"}},
            "Created": {"created_time": {}},
            "Status": {"status": {}},
        }
        
        try:
            new_db = self.client.databases.create(
                parent={"type": "page_id", "page_id": parent_page_id},
                title=[{"type": "text", "text": {"content": database_name}}],
                properties=db_properties
            )
            
            db_id = new_db['id']
            db_url = new_db.get('url', f"https://notion.so/{db_id.replace('-', '')}")
            logger.info(f"Created new database: {database_name}")
            return db_id, db_url
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def create_guide_page(
        self,
        database_id: str,
        guide: ApplicationGuide,
        video_metadata: dict,
    ) -> Tuple[str, Optional[str]]:
        """
        Create a Notion page with the Application Guide content.
        
        Args:
            database_id: Target Notion database ID
            guide: ApplicationGuide with synthesized content
            video_metadata: Video metadata (title, url, views, channel)
        Returns:
            Tuple of (guide page URL, transcript page URL). Transcript page URL is always None.
        """
        video_title = video_metadata.get('title', 'Untitled Guide')
        video_url = video_metadata.get('url', '')
        channel_name = video_metadata.get('channel_name', 'Unknown')
        view_count = video_metadata.get('view_count', 0)
        database_properties = self._get_database_properties(database_id)
        
        # Build page properties
        properties = {
            "Title": {
                "title": [{"text": {"content": f"{video_title} - Application Guide"}}]
            },
            "Channel": {
                "rich_text": [{"text": {"content": channel_name}}]
            },
            "Views": {"number": view_count},
        }

        status_property = self._build_status_property_value(database_properties)
        if status_property:
            properties["Status"] = status_property
        
        if video_url:
            properties["Video URL"] = {"url": video_url}
        
        # Build page content blocks
        children = self._build_page_blocks(guide, video_metadata)
        
        try:
            page = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children
            )
            
            page_url = page.get('url', f"https://notion.so/{page['id'].replace('-', '')}")
            logger.info(f"Created Notion page: {video_title}")
            return page_url, None
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            raise

    def _build_page_blocks(
        self,
        guide: ApplicationGuide,
        video_metadata: dict
    ) -> list[dict]:
        """
        Build Notion blocks for the Application Guide.
        
        Args:
            guide: ApplicationGuide content
            video_metadata: Video metadata
            
        Returns:
            List of Notion block objects
        """
        blocks = []
        
        # Video link callout
        video_url = video_metadata.get('url', '')
        thumbnail_url = video_metadata.get('thumbnail_url', '')
        
        if video_url:
            blocks.append({
                "type": "callout",
                "callout": {
                    "rich_text": [{"text": {"content": f"🎬 Watch Video: {video_url}"}}],
                    "icon": {"emoji": "📺"},
                    "color": "blue_background"
                }
            })
        
        # Thumbnail image if available
        if thumbnail_url:
            blocks.append({
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": thumbnail_url}
                }
            })
        
        blocks.append(self._divider())
        
        # Big Idea section
        blocks.append(self._heading1("💡 Big Idea"))
        blocks.append(self._paragraph(guide.big_idea))
        blocks.append(self._divider())
        
        # Key Timestamps section (if available)
        if guide.key_timestamps:
            blocks.append(self._heading2("⏱️ Key Timestamps"))
            for timestamp in guide.key_timestamps:
                blocks.append(self._bullet(timestamp))
            blocks.append(self._divider())
        
        # Tools & Apps section
        if guide.tools_and_apps:
            blocks.append(self._heading2("🛠️ Tools & Apps Used"))
            for tool in guide.tools_and_apps:
                tool_text = f"**{tool.name}** - {tool.purpose}"
                if tool.url:
                    tool_text += f" ({tool.url})"
                blocks.append(self._bullet(tool_text))
            blocks.append(self._divider())
        
        # Key Terms section
        blocks.append(self._heading2("📚 Key Terms"))
        for term in guide.key_terms:
            blocks.append(self._bullet(term))
        blocks.append(self._divider())
        
        # Apply in 5 Minutes section
        blocks.append(self._heading2("⚡ Apply in 5 Minutes"))
        blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": "Quick wins you can do RIGHT NOW:"}}],
                "icon": {"emoji": "🚀"},
                "color": "green_background"
            }
        })
        for action in guide.apply_5min:
            blocks.append(self._numbered(action))
        blocks.append(self._divider())
        
        # Implementation Steps section
        blocks.append(self._heading2("📋 Step-by-Step Implementation"))
        for i, step in enumerate(guide.implementation_steps, 1):
            blocks.append(self._numbered(step))
        blocks.append(self._divider())
        
        # Code Examples section
        if guide.code_snippets:
            blocks.append(self._heading2("💻 Code Examples"))
            
            for snippet in guide.code_snippets:
                # Language header with description
                header_text = f"{snippet.language.title()}"
                if snippet.description:
                    header_text += f" - {snippet.description}"
                blocks.append(self._heading3(header_text))
                
                # Code block
                blocks.append({
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": snippet.code[:2000]}}],
                        "language": self._normalize_language(snippet.language)
                    }
                })
                
                # Source indicator
                source_text = (
                    "📝 Extracted from video (verbatim)" 
                    if snippet.explicit_or_suggested == CodeSnippetType.EXPLICIT 
                    else "💡 Suggested example code"
                )
                blocks.append({
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"text": {"content": source_text}}],
                        "icon": {"emoji": "📝" if snippet.explicit_or_suggested == CodeSnippetType.EXPLICIT else "💡"},
                        "color": "gray_background"
                    }
                })
        
        # Resources section
        if guide.resources:
            blocks.append(self._divider())
            blocks.append(self._heading2("🔗 Resources & Links"))
            for resource in guide.resources:
                blocks.append(self._bullet(resource))
        
        # Footer
        blocks.append(self._divider())
        blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": "Generated by YouTube-to-Notion Guide Generator"}}],
                "icon": {"emoji": "🤖"},
                "color": "gray_background"
            }
        })
        
        return blocks

    def _heading1(self, text: str) -> dict:
        """Create a heading 1 block."""
        return {
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"text": {"content": text}}]
            }
        }
    
    def _heading2(self, text: str) -> dict:
        """Create a heading 2 block."""
        return {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"text": {"content": text}}]
            }
        }
    
    def _heading3(self, text: str) -> dict:
        """Create a heading 3 block."""
        return {
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"text": {"content": text}}]
            }
        }
    
    def _paragraph(self, text: str) -> dict:
        """Create a paragraph block."""
        return {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": text[:2000]}}]  # Notion limit
            }
        }
    
    def _bullet(self, text: str) -> dict:
        """Create a bulleted list item."""
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"text": {"content": text[:2000]}}]
            }
        }
    
    def _numbered(self, text: str) -> dict:
        """Create a numbered list item."""
        return {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [{"text": {"content": text[:2000]}}]
            }
        }
    
    def _divider(self) -> dict:
        """Create a divider block."""
        return {"type": "divider", "divider": {}}
    
    def _normalize_language(self, language: str) -> str:
        """
        Normalize language name to Notion's supported code languages.
        
        Args:
            language: Input language name
            
        Returns:
            Notion-compatible language identifier
        """
        # Notion's supported languages for code blocks
        supported_languages = {
            "abap", "abc", "agda", "arduino", "ascii art", "assembly", "bash", "basic", "bnf",
            "c", "c#", "c++", "clojure", "coffeescript", "coq", "css", "dart", "dhall", "diff",
            "docker", "ebnf", "elixir", "elm", "erlang", "f#", "flow", "fortran", "gherkin",
            "glsl", "go", "graphql", "groovy", "haskell", "hcl", "html", "idris", "java",
            "javascript", "json", "julia", "kotlin", "latex", "less", "lisp", "livescript",
            "llvm ir", "lua", "makefile", "markdown", "markup", "matlab", "mathematica", "mermaid",
            "nix", "notion formula", "objective-c", "ocaml", "pascal", "perl", "php", "plain text",
            "powershell", "prolog", "protobuf", "purescript", "python", "r", "racket", "reason",
            "ruby", "rust", "sass", "scala", "scheme", "scss", "shell", "smalltalk", "solidity",
            "sql", "swift", "toml", "typescript", "vb.net", "verilog", "vhdl", "visual basic",
            "webassembly", "xml", "yaml"
        }

        language = language.lower().strip()
        
        # Common mappings
        mappings = {
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "rb": "ruby",
            "yml": "yaml",
            "sh": "bash",
            "shell": "bash",
            "zsh": "bash",
            "golang": "go",
            "dockerfile": "docker",
            "text": "plain text",
            "txt": "plain text",
        }
        
        normalized_lang = mappings.get(language, language)

        if normalized_lang in supported_languages:
            return normalized_lang
        
        logger.warning(
            f"Unsupported language '{language}' normalized to '{normalized_lang}', "
            f"falling back to 'plain text'."
        )
        return "plain text"
