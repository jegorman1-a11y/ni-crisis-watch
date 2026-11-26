import unittest
from scripts.update import parse_feed
class FeedTest(unittest.TestCase):
    def test_atom(self):
        sample=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Warning update</title><link href="https://example.org/a" rel="alternate"/><updated>2026-11-26T01:00:00Z</updated></entry></feed>'''
        self.assertEqual(parse_feed(sample)[0]['title'],'Warning update')
    def test_rss(self):
        sample=b'<rss><channel><item><title>News headline</title><link>https://example.org/x</link></item></channel></rss>'
        self.assertEqual(parse_feed(sample)[0]['url'],'https://example.org/x')
if __name__=='__main__': unittest.main()
