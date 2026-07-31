# Bundled data

## Artist genre index

`engine/artist_index.json.gz` maps roughly 151,000 artist names to a genre.
It lets DJOrganizer recognise artists with no internet connection.

Derived from the MusicBrainz artist JSON data dump:
https://data.metabrainz.org/pub/musicbrainz/data/json-dumps/

MusicBrainz core data, which includes the artist genre and tag associations
used here, is released under Creative Commons Zero (CC0), a public domain
dedication: https://musicbrainz.org/doc/About/Data_License

CC0 requires no attribution. This notice is included anyway, because the
project exists thanks to that data and saying so costs nothing.

Rebuild it with:

    python3 tools/build_artist_index.py /path/to/artist.tar.xz

MusicBrainz publishes a fresh dump twice a week.
