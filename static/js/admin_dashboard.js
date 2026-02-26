function openModal(bookingId) {
    const modal = document.getElementById("confirmModal");
    const confirmLink = document.getElementById("confirmLink");

    // ✅ FIXED ROUTE
    confirmLink.href = "/admin-cancel/" + bookingId;

    modal.style.display = "flex";
}

function closeModal() {
    document.getElementById("confirmModal").style.display = "none";
}

/* Search filter */
document.getElementById("searchInput").addEventListener("keyup", function () {
    const value = this.value.toLowerCase();
    const rows = document.querySelectorAll("#bookingTable tr");

    rows.forEach(row => {
        row.style.display = row.innerText.toLowerCase().includes(value)
            ? ""
            : "none";
    });
});