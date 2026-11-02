from openpyxl import Workbook

from ai_agent.cleaner import MAX_DETAIL, MAX_NAME, clean_text

failures = 0


def check(name, passed):
    global failures
    if not passed:
        failures += 1
    print(f"{'✓' if passed else '✗'} {name}")


check(
    "Normal text remains unchanged",
    clean_text("2 cappuccinos and a croissant", MAX_DETAIL)
    == "2 cappuccinos and a croissant",
)

check(
    "Removes leading = to prevent formulas",
    clean_text('=HYPERLINK("http://x.com")', MAX_NAME)
    == 'HYPERLINK("http://x.com")',
)

check(
    "Removes leading + - @ characters",
    clean_text("+52 -1 @ana", MAX_NAME) == "52 -1 @ana",
)

check(
    "Collapses line breaks and repeated spaces",
    clean_text("coffee\n\n  order   details ", MAX_DETAIL)
    == "coffee order details",
)

check(
    "Removes invisible control characters",
    clean_text("hello\x00\x07world", MAX_NAME) == "helloworld",
)

check(
    "Truncates text exceeding the maximum length",
    len(clean_text("a" * 1000, MAX_DETAIL)) == MAX_DETAIL,
)

workbook = Workbook()
worksheet = workbook.active

worksheet.append(
    [
        '=HYPERLINK("http://x.com")',
        clean_text('=HYPERLINK("http://x.com")', MAX_NAME),
    ]
)

unclean_type = worksheet["A1"].data_type
clean_type = worksheet["B1"].data_type

print(
    f"   Without cleaning, Excel stores it as type '{unclean_type}' "
    f"(f = formula); after cleaning: '{clean_type}' (s = text)."
)

check(
    "Clean text is stored as text instead of an Excel formula",
    unclean_type == "f" and clean_type == "s",
)

print(
    "\nAll tests passed."
    if failures == 0
    else f"\n{failures} test(s) failed."
)

raise SystemExit(0 if failures == 0 else 1)