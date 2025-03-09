"""Readwise API client for Python."""

from readwise.api import ReadwiseReader
from readwise.model import DeleteRequest, DeleteResponse, Document, UpdateResponse
from readwise.version import __version__

__all__: list[str] = [
    "DeleteRequest",
    "DeleteResponse",
    "Document",
    "ReadwiseReader",
    "UpdateResponse",
    "__version__",
    "delete_document",
    "search_document",
    "update_document_location",
]

def delete_document(url: str | None = None, document_id: str | None = None) -> tuple[bool, dict | DeleteResponse]:
    """Delete a document from Readwise Reader.
    
    Args:
        url: URL of the document to delete (either url or document_id must be provided)
        document_id: ID of the document to delete
        
    Returns:
        Tuple of (success, response)
            - success: Boolean indicating if the operation was successful
            - response: Response data or error information
    """
    reader = ReadwiseReader()
    return reader.delete_document(url=url, document_id=document_id)

def update_document_location(document_id: str, location: str) -> tuple[bool, dict | UpdateResponse]:
    """Update a document's location in Readwise Reader.
    
    Args:
        document_id: ID of the document to update
        location: New location ('new' for inbox, 'later', 'archive')
        
    Returns:
        Tuple of (success, response)
            - success: Boolean indicating if the operation was successful
            - response: Response data or error information
    """
    reader = ReadwiseReader()
    return reader.update_document_location(document_id=document_id, location=location)

def search_document(url: str) -> tuple[bool, dict | Document]:
    """Search for a document by URL in Readwise Reader.
    
    Args:
        url: URL to search for
        
    Returns:
        Tuple of (success, document_data)
            - success: Boolean indicating if the document was found
            - document_data: Document information or error message
    """
    reader = ReadwiseReader()
    return reader.search_document(url=url)