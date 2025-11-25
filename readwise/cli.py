"""Command-line interface for Readwise."""

import json
import os
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

    Params:
        location (Optional[str]): The document's location, could be one of: new, later, shortlist, archive, feed
        category (Optional[str]): The document's category, could be one of: article, email, rss, highlight, note, pdf,
            epub, tweet, video
        updated_after (Optional[datetime]): Filter documents updated after a certain date.
        n (Optional[int]): Limits the number of documents to a maximum (100 by default).

    Usage:
        $ readwise list new
    """
    reader = ReadwiseReader(token=os.getenv(key="READWISE_TOKEN"))

    documents = reader.get_documents(location=location, category=category, updated_after=updated_after)[:n]
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
def save(url: str) -> None:
    """Save a document to Reader.

    Params:
        url (str): URL to the document from where it will be scraped by Readwise.

    Usage:
        $ readwise save "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    """
    reader = ReadwiseReader(token=os.getenv(key="READWISE_TOKEN"))
    success, document_info = reader.save_document(url=url)
    if success and document_info is not None:
        print(f"Document saved with ID {document_info.id!r} at {document_info.url!r}.")
    else:
        print(f"Failed to save document from {url!r}. Please check the URL and try again.")
