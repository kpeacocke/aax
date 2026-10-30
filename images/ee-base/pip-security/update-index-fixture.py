"""Use a maintained, pinned wheel for pip's index-provenance regression."""

from pathlib import Path
import sys


ORIGINAL = '''    @pytest.mark.network
    def test_download_info_index_url(self) -> None:
        """Test that download_info is set for requirements via index."""
        finder = make_test_finder(index_urls=["https://pypi.org/simple"])
        with self._basic_resolver(finder) as resolver:
            ireq = get_processed_req_from_line("initools")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert req.download_info.archive_info
'''


def patch(path: Path) -> None:
    source = path.read_text()
    if source.count(ORIGINAL) != 1:
        raise ValueError("Unexpected pip index-provenance test; review upstream fixture")
    updated = ORIGINAL.replace('"initools"', '"packaging==26.3"').replace(
        "        with self._basic_resolver(finder) as resolver:\n",
        "        with self._basic_resolver(finder) as resolver:\n"
        "            resolver.ignore_installed = True\n",
    )
    path.write_text(source.replace(ORIGINAL, updated))


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
