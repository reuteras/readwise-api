"""Models for the Readwise API."""

from pydantic import BaseModel, Field


class Tag(BaseModel):
    """A tag used to organize documents in Readwise Reader."""

    name: str
    type: str
    created: int


class Document(BaseModel):
    """A single document saved in the Readwise Reader."""

    id: str
    url: str
    title: str | None
    author: str | None
    source: str | None
    category: str
    location: str | None
    tags: dict[str, Tag] | None
    site_name: str | None
    word_count: int | None
    created_at: str
    updated_at: str
    notes: str | None
    published_date: int | str | None
    summary: str | None
    image_url: str | None
    content: str | None
    source_url: str | None
    parent_id: str | None
    saved_at: str
    last_moved_at: str
    reading_progress: float | None


class GetResponse(BaseModel):
    """A response from the Readwise API for GET requests.

    Fields:
        count (int): The number of returned documents (max 100).
        next_page_cursor (str | None): If there are more the 100 documents, a `next_page_cursor` is added to the
            response, which can be passed as a starting point for an additional request.
        results (list[Document]): The list of documents from Readwise.
    """

    count: int
    next_page_cursor: str | None = Field(..., alias="nextPageCursor")
    results: list[Document]


class PostRequest(BaseModel):
    """A POST request for the Readwise API to save documents to Reader.

    Fields:
        url (str): The document's unique URL. If you don't have one, you can provide a made up value such as
            https://yourapp.com#document1
        html (str | None): The document's content, in valid html (see examples). If you don't provide this, we will
            try to scrape the URL you provided to fetch html from the open web.
        should_clean_html  (Optional[bool]): Only valid when html is provided. Pass true to have us automatically
            clean the html and parse the metadata (title/author) of the document for you. By default, this option is
            false.
        title (str | None): The document's title, it will overwrite the original title of the document.
        author (str | None): The document's author, it will overwrite the original author (if found during the
            parsing step).
        summary (str | None): Summary of the document.
        published_date (str | None): A datetime representing when the document was published in the ISO 8601
            format; default timezone is UTC. Example: "2020-07-14T20:11:24+00:00"
        image_url (str | None): An image URL to use as cover image.
        location (str | None): One of: new, later, archive or feed. Default is new.
            Represents the initial location of the document (previously called triage_status). Note: if you try to use
            a location the user doesn't have enabled in their settings, this value will be set to their default
            location.
        saved_using (str | None): This value represents the source of the document
        tags (Optional[list[str]]): A list of strings containing tags, example: ["tag1", "tag2"]
    """

    url: str
    html: str | None = None
    should_clean_html: bool | None = None
    title: str | None = None
    author: str | None = None
    summary: str | None = None
    published_date: str | None = None
    image_url: str | None = None
    location: str | None = None
    saved_using: str | None = None
    tags: list[str] | None = None


class PostResponse(BaseModel):
    """A response from the Readwise API for POST requests.

    Fields:
        id (str): The ID of the saved document.
        url (str): The URL for the document in the Reader app.
    """

    id: str
    url: str

class DeleteRequest(BaseModel):
    """A request to delete a document from Readwise Reader."""
    
    id: str

class DeleteResponse(BaseModel):
    """A response from the Readwise API for DELETE requests."""
    
    success: bool
    message: str | None = None

class UpdateRequest(BaseModel):
    """A request to update a document's location in Readwise Reader."""
    
    id: str
    location: str
    
class UpdateResponse(BaseModel):
    """A response from the Readwise API for UPDATE requests."""
    
    success: bool
    message: str | None = None