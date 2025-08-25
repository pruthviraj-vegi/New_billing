$(function() {
  document.addEventListener("keydown", function(event) {
    if (event.ctrlKey && event.key === "F1" && search) {
          search.focus();
    }
    if (event.ctrlKey && event.key === "F2" && new_create) {
          window.location.href = new_create; // Redirect to the link URL
          return false;
    }
  });
});
