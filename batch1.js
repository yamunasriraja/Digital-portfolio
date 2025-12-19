const batchList = document.getElementById("batchList");

// Sortable
new Sortable(batchList, {
  animation: 200,
  ghostClass: "sortable-ghost",
});

// ------------------- ADD BATCH -------------------
function addBatch() {
  let newBatch = prompt("Enter new batch (e.g., 2025 - 2029)");
  if (!newBatch) return;

  fetch("/add_batch", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body:
      "name=" +
      encodeURIComponent(newBatch) +
      "&department=" +
      encodeURIComponent(document.body.dataset.department),
  }).then((res) => {
    if (res.ok) location.reload();
    else alert("Add failed");
  });
}

// ------------------- DELETE -------------------
document.querySelectorAll(".delete-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    let id = btn.dataset.id;
    if (!confirm("Delete this batch?")) return;

    fetch(`/delete_batch/${id}`, { method: "POST" }).then((res) => {
      if (res.ok) location.reload();
      else alert("Delete failed");
    });
  });
});

// ------------------- EDIT -------------------
document.querySelectorAll(".edit-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    let id = btn.dataset.id;
    let el = document.querySelector(`.batch-text[data-id="${id}"]`);
    let old = el.innerText;

    let input = document.createElement("input");
    input.value = old;
    input.className = "edit-input";

    el.replaceWith(input);
    input.focus();

    input.addEventListener("blur", () => saveEdit(input.value, id));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") saveEdit(input.value, id);
    });
  });
});

function saveEdit(value, id) {
  fetch(`/edit_batch/${id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: value }),
  }).then((res) => {
    if (res.ok) location.reload();
    else alert("Edit failed");
  });
}