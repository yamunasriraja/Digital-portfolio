// ---------------- EDIT SUBJECT ----------------
document.querySelectorAll(".edit-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    const subjectId = this.dataset.id;
    const oldName = this.dataset.name;

    const newName = prompt("Enter new subject name:", oldName);
    if (!newName || newName.trim() === "") return;

    fetch(`/edit_subject/${subjectId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name: newName.trim() }),
    })
      .then((res) => {
        if (res.ok) {
          location.reload();
        } else {
          alert("Subject update failed");
        }
      })
      .catch(() => alert("Server error"));
  });
});