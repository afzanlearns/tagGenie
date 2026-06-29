import pytest
from backend.slug import slugify


def test_basic_lowercase():
    assert slugify("Pokemon TCG") == "pokemon-tcg"


def test_replaces_spaces():
    assert slugify("specialty coffee") == "specialty-coffee"


def test_removes_accents():
    assert slugify("Café") == "cafe"
    assert slugify("façade") == "facade"
    assert slugify("cliché") == "cliche"


def test_unicode_to_ascii():
    assert slugify("Specialty Coffee & Café") == "specialty-coffee-cafe"
    assert slugify("München") == "munchen"
    assert slugify("naïve") == "naive"


def test_collapses_multiple_hyphens():
    assert slugify("a & b") == "a-b"
    assert slugify("x — y") == "x-y"
    assert slugify("foo && bar") == "foo-bar"


def test_removes_leading_trailing_hyphens():
    assert slugify("--hello--") == "hello"
    assert slugify("-foo-") == "foo"


def test_symbols_becomes_hyphen():
    assert slugify("coffee & tea") == "coffee-tea"
    assert slugify("up 2x fast!") == "up-2x-fast"


def test_multiple_punctuation():
    assert slugify("hello...world!!!") == "hello-world"
    assert slugify("a,b.c;d:e") == "a-b-c-d-e"


def test_repeated_hyphens_collapsed():
    assert slugify("foo---bar") == "foo-bar"
    assert slugify("a___b") == "a-b"


def test_empty_and_whitespace():
    assert slugify("") == "untitled"
    assert slugify("   ") == "untitled"


def test_only_symbols():
    assert slugify("&&&") == "untitled"


def test_deterministic():
    assert slugify("Coffee & Tea") == slugify("coffee & tea")
    assert slugify("Pokémon TCG") == slugify("pokemon tcg")


def test_user_collection_name():
    niche_slug = slugify("Specialty Coffee & Café")
    user_collection = f"user_9_{niche_slug}"
    assert user_collection == "user_9_specialty-coffee-cafe"


def test_preserves_underscore():
    assert slugify("hello_world") == "hello-world"


def test_numbers():
    assert slugify("elite trainer box v2") == "elite-trainer-box-v2"
    assert slugify("top 10 cards") == "top-10-cards"
