import os

html_file = "index.html"

with open(html_file, "r", encoding="utf-8") as f:
    text = f.read()

style_start = text.find("<style>")
style_end = text.find("</style>")
if style_start != -1 and style_end != -1:
    css = text[style_start+7:style_end].strip("\n")
    with open("styles.css", "w", encoding="utf-8") as f:
        f.write(css + "\n")
    text = text[:style_start] + '<link rel="stylesheet" href="styles.css" />' + text[style_end+8:]
    print("styles.css extracted")
else:
    print("No <style> block found")

script_start = text.find("<script>\n      // ═══════════════════════════════════════")
if script_start == -1:
    # Try finding the generic last script block if specific one not found
    script_start = text.rfind("<script>")

if script_start != -1:
    script_end = text.find("</script>", script_start)
    if script_end != -1:
        js = text[script_start+8:script_end].strip("\n")
        with open("script.js", "w", encoding="utf-8") as f:
            f.write(js + "\n")
        text = text[:script_start] + '<script src="script.js"></script>' + text[script_end+9:]
        print("script.js extracted")
    else:
        print("No </script> matching the script_start found")
else:
    print("No <script> block found")

with open(html_file, "w", encoding="utf-8") as f:
    f.write(text)

print("Done splitting")
