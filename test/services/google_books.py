import requests


def fetch_book_details(book_name):

    url = (
        f"https://openlibrary.org/search.json"
        f"?title={book_name}"
    )

    response = requests.get(url)

    data = response.json()

    if not data["docs"]:
        return None

    book = data["docs"][0]
    print(book)
    return {

        "title": book.get(
            "title",
            ""
        ),

        "author": ", ".join(
            book.get(
                "author_name",
                []
            )
        ),

        "category": "",

        "isbn": (
            book.get(
                "isbn",
                [""]
            )[0]
            if book.get("isbn")
            else ""
        )

    }