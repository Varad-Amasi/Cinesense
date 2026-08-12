# Dumps a Letterboxd film review page to lb_dump.html using cloudscraper.
import cloudscraper
import os

def dump_lb():
    scraper = cloudscraper.create_scraper()
    url = "https://letterboxd.com/film/john-wick-chapter-4/reviews/by/activity/page/1/"
    resp = scraper.get(url)
    with open("lb_dump.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Dumped to lb_dump.html")


if __name__ == "__main__":
    dump_lb()
