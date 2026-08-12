import requests

IMDB_GRAPHQL_URL = "https://api.graphql.imdb.com/"

REVIEWS_QUERY = """
query Reviews($titleId: ID!, $first: Int!) {
  title(id: $titleId) {
    reviews(first: $first) {
      edges {
        node {
          text {
            originalText {
              plainText
            }
          }
        }
      }
    }
  }
}
"""

def test_pagination():
    variables = {"titleId": "tt1160419", "first": 50}
    resp = requests.post(
        IMDB_GRAPHQL_URL,
        json={"query": REVIEWS_QUERY, "variables": variables},
        headers={"Content-Type": "application/json"},
    )
    data = resp.json()
    print(data)

if __name__ == "__main__":
    test_pagination()
