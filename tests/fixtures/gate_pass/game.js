const params = new URLSearchParams(location.search);
const diff = params.get("difficulty") || "beginner";
document.getElementById("diff").value = diff;
document.getElementById("diff").addEventListener("change", (e) => {
  const url = new URL(location.href);
  url.searchParams.set("difficulty", e.target.value);
  history.replaceState(null, "", url);
});
