"""Command-line interface for Readwise."""

import json
import os
import sys
from datetime import datetime
from typing import Annotated

import typer

from readwise.api import ReadwiseReader

app = typer.Typer()


@app.command()
def list(
    location: Annotated[str | None, typer.Option("--location", "-l")] = None,
    category: Annotated[str | None, typer.Option("--category", "-c")] = None,
    updated_after: Annotated[datetime | None, typer.Option("--updated-after", "-u")] = None,
    n: Annotated[int | None, typer.Option("--number", "-n")] = None,
) -> None:
    """List documents.

    Args:
        location: The document's location, could be one of: new, later, shortlist, archive, feed
        category: The document's category, could be one of: article, email, rss, highlight, note, pdf,
            epub, tweet, video
        updated_after: Filter documents updated after a certain date.
        n: Limits the number of documents to a maximum (1-100). If not specified, returns all documents.

    Usage:
        $ readwise list new
        $ readwise list --location archive --number 50
    """
    reader = ReadwiseReader(token=os.getenv(key="READWISE_TOKEN"))

    if n is not None and not (1 <= n <= 100):  # noqa: PLR2004
        print(f"Error: --number must be between 1 and 100, got {n}")
        sys.exit(1)

    documents = reader.get_documents(location=location, category=category, updated_after=updated_after, limit=n)
    fields_to_include: set[str] = {
        "title",
        "id",
        "category",
        "author",
        "source",
        "created_at",
        "updated_at",
        "reading_progress",
    }
    print(json.dumps(obj=[d.dict(include=fields_to_include) for d in documents], indent=2))


@app.command()
def get(id: str) -> None:
    """Get a single document from its ID.

    Usage:
        $ readwise get <document_id>
    """
    reader = ReadwiseReader(token=os.getenv(key="READWISE_TOKEN"))

    doc = reader.get_document_by_id(id=id)
    if doc:
        print(doc.model_dump_json(indent=2))
    else:
        print(f"No document with ID {id!r} could be found.")


@app.command()
def save(
    url: Annotated[str | None, typer.Option("--url", "-u")] = None,
    html_file: Annotated[str | None, typer.Option("--html-file", "-f")] = None,
    title: Annotated[str | None, typer.Option("--title", "-t")] = None,
    author: Annotated[str | None, typer.Option("--author", "-a")] = None,
    tags: Annotated[str | None, typer.Option("--tags", "-g")] = None,
) -> None:
    """Save a document to Reader.

    Either --url or --html-file must be provided.

    Args:
        url: URL to the document from where it will be scraped by Readwise.
        html_file: Path to HTML file to upload instead of scraping a URL.
        title: Override document title.
        author: Override document author.
        tags: Comma-separated list of tags to apply.

    Usage:
        $ readwise save --url "https://example.com/article"
        $ readwise save --html-file content.html --title "My Article" --tags "tag1,tag2"
    """
    reader = ReadwiseReader(token=os.getenv(key="READWISE_TOKEN"))

    # Parse HTML file if provided
    html_content = None
    if html_file:
        try:
            with open(html_file, encoding="utf-8") as f:
                html_content = f.read()
        except FileNotFoundError:
            print(f"Error: HTML file '{html_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            sys.exit(1)

    # Validate that either url or html_file is provided
    if not url and not html_file:
        print("Error: Either --url or --html-file must be provided.")
        sys.exit(1)

    # Parse tags if provided
    tag_list = None
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    try:
        success, document_info = reader.save_document(
            url=url,
            html=html_content,
            title=title,
            author=author,
            tags=tag_list,
        )
        if success and document_info is not None:
            print(f"Document saved with ID {document_info.id!r} at {document_info.url!r}.")
        else:
            print("Failed to save document. Please check your parameters and try again.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


@app.command()
def auth_check() -> None:
    """Check if the Readwise token is valid.

    Uses the READWISE_TOKEN environment variable.

    Exit codes:
        0: Token is valid
        1: Token is invalid or missing

    Usage:
        $ readwise auth-check
    """
    try:
        reader = ReadwiseReader(token=os.getenv(key="READWISE_TOKEN"))
        if reader.validate_token():
            print("Token is valid.")
            sys.exit(0)
        else:
            print("Token is invalid.")
            sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
