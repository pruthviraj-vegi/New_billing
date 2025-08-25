const limit = 30;
let start = 0;
let action = "inactive";
let sort_column;
let sort_order = "Dec";
let tableBody = $("#table_body");

// sourcery skip: avoid-function-declarations-in-blocks
function reverse(value) {
  if (value == sort_column) {
    sort_order = sort_order === "Dec" ? "Asc" : "Dec";
  }
}

function getAllSearchParams() {
  let params = new URLSearchParams();

  // Add basic search parameters
  if (search.val()) {
    params.append("search", search.val());
  }

  // Add limit, start, and sorting parameters
  if (typeof limit !== "undefined") params.append("limit", limit);
  if (typeof start !== "undefined") params.append("start", start);
  if (typeof sort_column !== "undefined")
    params.append("sort_column", sort_column);
  if (typeof sort_order !== "undefined") params.append("sort_type", sort_order);

  // Add custom search parameters
  if (typeof customSearch !== "undefined") {
    for (let key in customSearch) {
      if (customSearch.hasOwnProperty(key) && customSearch[key].val()) {
        // Handle multiple select values for category
        if (key === "category") {
          const selectedCategories = customSearch[key].val();
          if (selectedCategories) {
            selectedCategories.forEach((value) => {
              params.append("category[]", value);
            });
          }
        } else {
          params.append(key, customSearch[key].val());
        }
      }
    }
  }

  // Add min/max search parameters
  if (typeof minMaxSearch !== "undefined") {
    for (let key in minMaxSearch) {
      if (minMaxSearch.hasOwnProperty(key) && minMaxSearch[key] > 0) {
        params.append(key, minMaxSearch[key]);
      }
    }
  }

  // Add hidden content parameter
  if (typeof hidden_content !== "undefined" && hidden_content === false) {
    params.append("hidden_content", hidden_content);
  }

  return params;
}

if (typeof search_url !== "undefined") {
  function load_post_data() {
    // sourcery skip: avoid-using-var
    let params = getAllSearchParams();
    let requestData = {};

    // Convert URLSearchParams to plain object
    for (let [key, value] of params) {
      requestData[key] = value;
    }

    $.ajax({
      url: search_url,
      method: "GET",
      data: requestData,
      cache: false,
      success: function (response) {
        // Check for empty string, empty array, or "No data found" in HTML
        if (
          !response ||
          (Array.isArray(response) && response.length === 0) ||
          (typeof response === "string" && (response.trim() === "" || response.includes("No data found")))
        ) {
          // Display "No data found" message
          if (start === 0) {
            // Only show message on first load or search reset
            tableBody.html('<tr><td colspan="9" class="text-center">No data found</td></tr>');
          }
          action = "end"; // No more data to load
          return;
        }
        tableBody.append(response);
        action = "inactive";
      },
    });
  }

  load_post_data();

  $(window).scroll(function () {
    const { scrollHeight, scrollTop, clientHeight } = document.documentElement;
    if (
      scrollTop + clientHeight >= scrollHeight - 150 &&
      action == "inactive"
    ) {
      action = "active";
      start += limit;
      load_post_data();
    }
  });

  $("#table__data").on("click", ".sort-link", function (e) {
    e.preventDefault();
    $("#table_body").empty();
    const column = $(this).data("column");
    sort_column = column;
    reverse(sort_column);
    start = 0;
    load_post_data();
  });

  function table_reset() {
    tableBody.empty();
    start = 0;
    load_post_data();
  }

  $(document).on("submit", "#search-form", function (e) {
    e.preventDefault();
    table_reset();
  });

  $(document).on("submit", "#custom_search", function (e) {
    e.preventDefault();
    table_reset();
  });
}

if (typeof suggest_url !== "undefined") {
  $.ajax({
    url: suggest_url,
    method: "GET",
    data: {
      suggestion: null,
    },
    cache: false,
    success: function (response) {
      customAutoComplete(search, response);
    },
  });
}

function sortTable(table, column) {
  const tableBody = table.querySelector("tbody");
  const rows = Array.from(tableBody.querySelectorAll("tr"));

  const sortDirection = table.getAttribute("data-sort-direction");
  const sortOrder = sortDirection === "ascending" ? 1 : -1;

  const newRows = rows.sort((rowA, rowB) => {
    const cellA = rowA.querySelectorAll("td")[column];
    const cellB = rowB.querySelectorAll("td")[column];

    let valueA = cellA.textContent.trim().replace(/,/g, "");
    let valueB = cellB.textContent.trim().replace(/,/g, "");

    const isNumericA = !isNaN(parseFloat(valueA));
    const isNumericB = !isNaN(parseFloat(valueB));

    if (isNumericA && isNumericB) {
      valueA = parseFloat(valueA);
      valueB = parseFloat(valueB);
      return sortOrder * (valueA - valueB);
    } else if (!isNumericA && !isNumericB) {
      return sortOrder * valueA.localeCompare(valueB);
    } else {
      // Sort non-numeric values before numeric values
      return isNumericA ? 1 : -1;
    }
  });

  tableBody.innerHTML = "";

  newRows.forEach((row) => {
    tableBody.appendChild(row);
  });

  const newSortDirection =
    sortDirection === "ascending" ? "descending" : "ascending";
  table.setAttribute("data-sort-direction", newSortDirection);
}

const table = document.querySelector(".custom-sorting");
if (table) {
  const headers = table.querySelectorAll("th");
  headers.forEach((th, idx) => {
    th.addEventListener("click", () => {
      const currentIsAscending = th.classList.contains("th-sort-asc");
      sortTable(table, idx, !currentIsAscending);
    });
  });
}

if (typeof minMaxUrl !== "undefined") {
  $.ajax({
    url: minMaxUrl,
    method: "GET",
    caches: true,
    success: function (response) {
      $("#range_03").ionRangeSlider({
        type: "double",
        grid: true,
        min: 0,
        max: parseInt(response.max_price) + 1000,
        from: 0,
        to: response.max_price,
        prefix: "Rs",
      });
    },
  });
}
function downloadFile(type) {
  // Get all search parameters
  let params = getAllSearchParams();

  // Determine URL based on type
  let baseUrl;
  if (type === "pdf") {
    baseUrl = download_url.pdf;
  } else if (type === "excel") {
    baseUrl = download_url.excel;
  }

  if (baseUrl) {
    // Create and trigger download
    let downloadUrl = `${baseUrl}?${params.toString()}`;
    window.open(downloadUrl, "_blank");
  } else {
    CalledToast("error", "No download url found");
  }
}
