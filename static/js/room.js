$(function () {
  // Utility function to filter out empty values from an object
  function filterEmptyValues(obj) {
    const filtered = {};
    for (const [key, value] of Object.entries(obj)) {
      if (value !== null && value !== undefined && value.toString().trim() !== '') {
        filtered[key] = value;
      }
    }
    return filtered;
  }

  // fetch the initial stock values
  $.ajax({
    url: fetch_all_stock_url,
    method: "GET",
    cache: false,
    success: function (response) {
      tableBody.append(response);
      CalculateRoomData();
    },
  });
  // search the stock from backend
  $(document).on("submit", "#search_form", function (e) {
    e.preventDefault();

    const searchValue = $("#search").val();
    // Only proceed if search value is not empty
    if (!searchValue || searchValue.trim() === '') {
      CalledToast("info", "Please enter a search term");
      return;
    }

    $.ajax({
      url: search_stock_url,
      method: "GET",
      data: {
        search_id: searchValue,
        room_id: model_id,
      },
      cache: false,
      success: function (response) {
        if (response.status == 400) {
          CalledToast("info", "No Data Found On Searched Data");
          $("#present_stock_qty").hide();
        } else {
          tableBody.prepend(response);
          $("#search").val("");
          CalculateRoomData();
        }
      },
    });
  });

  // check the clicked button and assign the respective value
  $("#table_body").on("click", "button", function (event) {
    const buttonName = $(this).text().trim();
    const trElement = $(this).closest("tr");
    const dataId = parseInt(trElement.attr("data-item-id"));

    if (buttonName == "Edit") {
      validateUpdate(dataId);
    } else if (buttonName == "Delete") {
      deleteRow(dataId, trElement);
      CalculateRoomData();
    }
  });

  // delete the stock from table
  function deleteRow(id, row) {
    $.ajax({
      url: delete_stock_url,
      method: "POST",
      data: {
        stock_id: id,
        csrfmiddlewaretoken: csrftoken,
      },
      cache: false,
      success: function (response) {
        if (response.status == 200) {
          row.remove();
          $("#search").focus();
          CalculateRoomData();
        } else {
          CalledToast("error", "failed to delete");
        }
      },
    });
  }

  // assign the validate to the table
  $("#table_body").on("keypress", "input", function (event) {
    if (event.which === 13 || event.keyCode === 13) {
      const trElement = $(this).closest("tr");
      const dataId = parseInt(trElement.attr("data-item-id"));
      validateUpdate(dataId);
    }
  });

  // initial the check to the validate updates
  function validateUpdate(id) {
    const row = $(`tr[data-item-id="${id}"]`);
    const inputs = row.find("input");
    let hasEmptyOrZeroValue = false;

    inputs.each(function () {
      const value = $(this).val().trim();
      if (value === "" || parseFloat(value) <= 0) {
        hasEmptyOrZeroValue = true;
        $(this).focus();
        return false;
      }
    });

    if (hasEmptyOrZeroValue) {
      CalledToast("error", "Some Fields are empty or Zero");
    } else {
      updateRow(id, row);
    }
  }

  // update the stock values
  function updateRow(row_id, row) {
    // Add input validation
    if (!row_id || !row) {
      CalledToast("error", "Invalid row data");
      return;
    }

    const quantityInput = row.find('input[name="quantity"]');
    const priceInput = row.find('input[name="price"]');
    const sizeVariant = row.find("option:selected");

    // Validate inputs
    const quantityValue = parseFloat(quantityInput.val()) || 0;
    const priceValue = parseFloat(priceInput.val()) || 0;
    const sizeValue = parseFloat(sizeVariant.val());

    // Add error handling for AJAX
    $.ajax({
      url: update_stock_url,
      method: "POST",
      data: {
        stock_id: row_id,
        quantity: quantityValue,
        price: priceValue,
        size: sizeValue,
        csrfmiddlewaretoken: csrftoken,
      },
      cache: false,
      success: function (response) {
        if (response.status == 200) {
          updateUIElements(row, response, quantityValue);
        } else {
          CalledToast("error", response.message || "Failed updating");
        }
      },
      error: function (xhr, status, error) {
        CalledToast("error", "Server error occurred");
      },
    });
  }

  // Separate UI update logic
  function updateUIElements(row, response) {
    row.find("#amount").text(parseFloat(response.data.amount).toFixed(2));
    row.find("#discount").text(parseFloat(response.data.discount).toFixed(2));

    CalledToast("success", response.data.barcode + " updated successfully");
    $("#search").focus();
    CalculateRoomData();

    const presentQtyElement = $("#present_stock_qty");
    if (presentQtyElement.length) {
      presentQtyElement
        .text("Present Stock: " + response.data.present_quantity)
        .toggleClass("text-danger", response.data.present_quantity < 0)
        .show();
    }
  }

  // press ctrl+f10 to open custom search details
  document.addEventListener("keydown", function (event) {
    if (event.key === "F10") {
      event.preventDefault();
      simulateSearchClick();
    }
  });

  // search the click options
  function simulateSearchClick() {
    if (searchButton) {
      searchButton.click();
      // Focus on first input immediately after modal opens
      setTimeout(function () {
        $('#search_id').focus().select();
      }, 100);
    }
  }

  // assigning the search to the search bill stock
  $(document).on("submit", "#search_bill_stock", function (e) {
    e.preventDefault();
    costumeStockSearch();
  });

  var customSearch = {
    id_type: $("#search_id"),
    barcode: $("#search_barcode"),
    mainType: $("#search_main_Type"),
    subType: $("#search_sub_Type"),
    quantity: $("#search_quantity"),
    price: $("#search_price"),
    discount: $("#search_discount"),
  };

  // calling the custom search function
  function costumeStockSearch() {
    // sourcery skip: avoid-using-var
    var requestData = {};

    for (var key in customSearch) {
      if (customSearch.hasOwnProperty(key)) {
        requestData[key] = customSearch[key].val();
      }
    }

    // Filter out empty values before sending
    requestData = filterEmptyValues(requestData);

    // making the custom search data to view
    $.ajax({
      url: custom_search_url,
      method: "GET",
      data: requestData,
      cache: false,
      success: function (response) {
        search_table.empty();
        search_table.append(response);
      },
    });
  }

  // calculate the sum of room amounts
  function CalculateRoomData() {
    const amounts = $("#table_body #amount");
    const items = $("#table_body #quantity");

    let total_amount = 0;
    let total_items = 0;
    for (let i = 0; i < amounts.length; i++) {
      total_amount += parseFloat(amounts[i].innerHTML);
    }
    for (let i = 0; i < items.length; i++) {
      total_items += parseFloat(items[i].value);
    }

    updateAllCounters({
      total_amount: total_amount,
      total_items: total_items,
    });

    if (room_id) {
      $("#room_" + room_id).text(
        total_amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      );
    }
  }

  // shift with enter to submit bill
  document.addEventListener("keypress", function (event) {
    // Check if the Shift key (event.shiftKey) and the Enter key (event.key === 'Enter') were pressed simultaneously
    if (event.shiftKey && event.key === "Enter") {
      if (parseInt($("#total_amount").text()) !== 0) {
        const link = document.getElementById("submitBillLink");
        link.click();
      } else {
        CalledToast("info", "No bills to Submit Stock");
      }
    }
  });

  // calls the bookmarks stock
  $.ajax({
    url: fetch_bookmark_stock,
    method: "GET",
    cache: false,
    success: function (response) {
      $("#bookmarks_body").append(response);
      $("#bookmark-close").click();
    },
  });

  // ===== MODAL AND KEYBOARD NAVIGATION FUNCTIONALITY =====

  // Price hover functionality
  const $document = $(document)

  $document.on('mouseenter', '.price-hover', function () {
    const $this = $(this)
    const $popup = $this.find('.price-popup')

    positionPopup($this, $popup)
    fetchPriceHistory($this, $popup)
  })

  $document.on('mouseleave', '.price-hover', function () {
    const $popup = $(this).find('.price-popup')
    $popup.hide()
  })

  // Enhanced modal functionality
  $('#stockSearchModal').on('show.bs.modal', function () {
    // Store the element that had focus before modal opens
    $(this).data('previousFocus', document.activeElement)
    // Remove aria-hidden when modal is showing
    $(this).removeAttr('aria-hidden')
  })

  $('#stockSearchModal').on('shown.bs.modal', function () {
    // Focus on the first search field when modal opens and select all text
    setTimeout(function () {
      $('#search_id').focus().select()
    }, 50)

    // Add keyboard shortcuts
    $(this).on('keydown', function (e) {
      // ESC key to close modal
      if (e.key === 'Escape') {
        $(this).modal('hide')
      }

      // Ctrl+Enter to submit search
      if (e.ctrlKey && e.key === 'Enter') {
        $('#search_bill_stock').submit()
      }
    })
  })

  // Handle Ctrl+F10 shortcut globally
  $(document).on('keydown', function (e) {
    if (e.ctrlKey && e.key === 'F10') {
      e.preventDefault()
      $('#searchFilter').click()
    }
  })

  // Handle F10 shortcut globally (as per user's change)
  $(document).on('keydown', function (e) {
    if (e.key === 'F10') {
      e.preventDefault()
      $('#searchFilter').click()
    }
  })

  // Keyboard navigation for search results
  let currentRowIndex = -1
  let searchResults = []

  $(document).on('keydown', '#stockSearchModal', function (e) {
    const $searchBody = $('#search_body')
    const $rows = $searchBody.find('tr')

    if ($rows.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        if (currentRowIndex < $rows.length - 1) {
          currentRowIndex++
          highlightRow($rows, currentRowIndex)
        }
        break

      case 'ArrowUp':
        e.preventDefault()
        if (currentRowIndex > 0) {
          currentRowIndex--
          highlightRow($rows, currentRowIndex)
        }
        break

      case 'Enter':
        if (currentRowIndex >= 0 && currentRowIndex < $rows.length) {
          e.preventDefault()
          const $selectedRow = $rows.eq(currentRowIndex)
          const barcode = $selectedRow.find('td:eq(1)').text().trim()
          if (barcode) {
            selectedStock(barcode)
          }
        }
        break
    }
  })

  // Function to highlight the selected row
  function highlightRow($rows, index) {
    $rows.removeClass('table-active')
    if (index >= 0 && index < $rows.length) {
      $rows.eq(index).addClass('table-active')
      // Scroll to the selected row if needed
      const $selectedRow = $rows.eq(index)
      const container = document.querySelector('#stockSearchModal .modal-body')
      const rowTop = $selectedRow.offset().top
      const containerTop = $(container).offset().top
      const containerHeight = $(container).height()

      if (rowTop < containerTop || rowTop > containerTop + containerHeight) {
        container.scrollTop = $selectedRow.position().top - container.height() / 2
      }
    }
  }

  // Reset row selection when new search results are loaded
  const searchBodyObserver = new MutationObserver(function (mutations) {
    currentRowIndex = -1
    $('#search_body tr').removeClass('table-active')
  });

  // Start observing the search body for changes
  const searchBody = document.getElementById('search_body');
  if (searchBody) {
    searchBodyObserver.observe(searchBody, {
      childList: true,
      subtree: true
    });
  }

  // Click functionality for table rows
  $(document).on('click', '#search_body tr', function () {
    const $rows = $('#search_body tr')
    const clickedIndex = $rows.index(this)

    // Update current row index
    currentRowIndex = clickedIndex

    // Highlight the clicked row
    $rows.removeClass('table-active')
    $(this).addClass('table-active')

    // Get the barcode from the clicked row
    const barcode = $(this).find('td:eq(1)').text().trim()
    if (barcode) {
      // Don't auto-select, just highlight - user can press Enter to select
    }
  })

  // Double-click to select item
  $(document).on('dblclick', '#search_body tr', function () {
    const barcode = $(this).find('td:eq(1)').text().trim()
    if (barcode) {
      selectedStock(barcode)
    }
  })

  // Clear search results when modal is hidden
  $('#stockSearchModal').on('hidden.bs.modal', function () {
    $('#search_body').empty()
    $('#search_bill_stock')[0].reset()
    currentRowIndex = -1

    // Restore focus to the previous element
    const previousFocus = $(this).data('previousFocus')
    if (previousFocus && previousFocus.focus) {
      previousFocus.focus()
    }

    // Add aria-hidden back when modal is hidden
    $(this).attr('aria-hidden', 'true')
  })

  // Auto-submit search on input change (with debounce)
  let searchTimeout
  $('#stockSearchModal input').on('input', function () {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(function () {
      if ($('#search_id').val() || $('#search_barcode').val() || $('#search_main_Type').val() || $('#search_sub_Type').val()) {
        $('#search_bill_stock').submit()
      }
    }, 500)
  })

  // Add loading indicator
  $(document).on('submit', '#search_bill_stock', function () {
    $('#search_body').html('<tr><td colspan="10" class="text-center"><i class="fas fa-spinner fa-spin"></i> Searching...</td></tr>')
  })

  // ===== BOOKMARK MODAL FUNCTIONALITY =====

  // Bookmark modal functionality
  let bookmarkCurrentRowIndex = -1

  // Keyboard navigation for bookmark results
  $(document).on('keydown', '#bookmark-dialog', function (e) {
    const $bookmarkBody = $('#bookmarks_body')
    const $rows = $bookmarkBody.find('tr')

    if ($rows.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        if (bookmarkCurrentRowIndex < $rows.length - 1) {
          bookmarkCurrentRowIndex++
          highlightBookmarkRow($rows, bookmarkCurrentRowIndex)
        }
        break

      case 'ArrowUp':
        e.preventDefault()
        if (bookmarkCurrentRowIndex > 0) {
          bookmarkCurrentRowIndex--
          highlightBookmarkRow($rows, bookmarkCurrentRowIndex)
        }
        break

      case 'Enter':
        if (bookmarkCurrentRowIndex >= 0 && bookmarkCurrentRowIndex < $rows.length) {
          e.preventDefault()
          const $selectedRow = $rows.eq(bookmarkCurrentRowIndex)
          // Get the barcode from the onclick attribute of the Select link
          const $selectLink = $selectedRow.find('a.copyable')
          const onclickAttr = $selectLink.attr('onclick')
          if (onclickAttr) {
            // Extract barcode from onclick="selectedStock('BARCODE')"
            const match = onclickAttr.match(/selectedStock\('([^']+)'\)/)
            if (match && match[1]) {
              selectedBookmarkStock(match[1])
            }
          }
        }
        break
    }
  })

  // Function to highlight the selected bookmark row
  function highlightBookmarkRow($rows, index) {
    $rows.removeClass('bookmark-active')
    if (index >= 0 && index < $rows.length) {
      $rows.eq(index).addClass('bookmark-active')
      // Scroll to the selected row if needed
      const $selectedRow = $rows.eq(index)
      const container = document.querySelector('#bookmark-dialog .modal-body')
      const rowTop = $selectedRow.offset().top
      const containerTop = $(container).offset().top
      const containerHeight = $(container).height()

      if (rowTop < containerTop || rowTop > containerTop + containerHeight) {
        container.scrollTop = $selectedRow.position().top - container.height() / 2
      }
    }
  }

  // Click functionality for bookmark table rows
  $(document).on('click', '#bookmarks_body tr', function () {
    const $rows = $('#bookmarks_body tr')
    const clickedIndex = $rows.index(this)

    // Update current row index
    bookmarkCurrentRowIndex = clickedIndex

    // Highlight the clicked row
    $rows.removeClass('bookmark-active')
    $(this).addClass('bookmark-active')
  })

  // Double-click to select bookmark item
  $(document).on('dblclick', '#bookmarks_body tr', function () {
    const $selectLink = $(this).find('a.copyable')
    const onclickAttr = $selectLink.attr('onclick')
    if (onclickAttr) {
      const match = onclickAttr.match(/selectedStock\('([^']+)'\)/)
      if (match && match[1]) {
        selectedBookmarkStock(match[1])
      }
    }
  })

  // Reset bookmark row selection when modal is hidden
  $('#bookmark-dialog').on('hidden.bs.modal', function () {
    bookmarkCurrentRowIndex = -1
    $('#bookmarks_body tr').removeClass('bookmark-active')
    // Add aria-hidden back when modal is hidden
    $(this).attr('aria-hidden', 'true')
  })

  // Add show event handler for bookmark modal
  $('#bookmark-dialog').on('show.bs.modal', function () {
    // Remove aria-hidden when modal is showing
    $(this).removeAttr('aria-hidden')
  })

  // Function to select bookmark stock
  function selectedBookmarkStock(barcode) {
    search.val(barcode)
    $('#bookmark-dialog').modal('hide')
    $('#submit-button').click()
  }

  // Cleanup MutationObserver when page is unloaded
  $(window).on('beforeunload', function () {
    if (searchBodyObserver) {
      searchBodyObserver.disconnect();
    }
  });
});

//empty the custom search values and the table also
function resetForm() {
  // Get the form element by its ID
  const form = document.getElementById("search_bill_stock");

  search_table.empty();

  // Reset the form using the 'reset' method
  form.reset();
}

// select the barcode and close the the model
function selectedStock(stock_data) {
  search_table.empty();
  search.val(stock_data);

  closeModels();
  $("#submit-button").click();
  resetForm();
}

function closeModels() {
  // Close modal
  const modal = bootstrap.Modal.getInstance(document.getElementById('stockSearchModal'));
  if (modal) {
    modal.hide();
  }

  // Also close any other modals that might be open
  const buttons = document.querySelectorAll(".btn-close");
  buttons.forEach((button) => {
    button.click();
  });
}

// toggle the search option
function toggleFocus() {
  // Check if modal is visible
  if ($('#stockSearchModal').hasClass('show') || $('#stockSearchModal').is(':visible')) {
    // Modal is shown, so focus on customSearchId and select text
    customSearchId.focus().select();
  } else {
    // Modal is not shown, so focus on the search element
    search.focus();
  }
}

// assigning the prices for the variants
function assignPrice(selectElement) {
  var selectedOption = $(selectElement).find("option:selected");
  var selectedAmount = selectedOption.attr("data-amount");
  var selectedBarcode = selectedOption.attr("data-barcode");
  var selectedRate = selectedOption.attr("data-discount");
  var selectTr = selectedOption.closest("tr");

  // Update the price and barcode
  selectTr
    .find(".mrp")
    .text(selectedAmount.toLocaleString("en-IN"))
    // Reset the loaded state so popup can fetch new data
    .data("loaded", false)
    // Update the data-barcode attribute
    .attr("data-barcode", selectedBarcode);

  selectTr
    .find(".barcode")
    .text(selectedBarcode)
    .attr("data-barcode", selectedBarcode);

  selectTr.find("#price").val(selectedRate);
  // Trigger the save
  selectTr.find(".save-item-btn").click();
}

// clipboard function
function copyToClipboard(element) {
  const text = element.innerText;

  navigator.clipboard
    .writeText(text)
    .then(() => {
      CalledToast("success", text + " Copied to Clipboard");
    })
    .catch((err) => {
      CalledToast("failed", err);
    });
}

// Position popup function for price hover
function positionPopup($trigger, $popup) {
  const triggerOffset = $trigger.offset();
  const triggerHeight = $trigger.outerHeight();
  const popupHeight = $popup.outerHeight();
  const windowHeight = $(window).height();
  const windowWidth = $(window).width();

  // Calculate position
  let top = triggerOffset.top + triggerHeight + 5;
  let left = triggerOffset.left;

  // Adjust if popup would go below window
  if (top + popupHeight > windowHeight) {
    top = triggerOffset.top - popupHeight - 5;
  }

  // Adjust if popup would go outside window width
  if (left + $popup.outerWidth() > windowWidth) {
    left = windowWidth - $popup.outerWidth() - 10;
  }

  // Position the popup
  $popup.css({
    position: 'absolute',
    top: top + 'px',
    left: left + 'px',
    zIndex: 9999
  }).show();
}

// Generic function to fetch and populate price history
function fetchPriceHistory($trigger, $popup) {
  if (!$trigger.data("loaded")) {
    // Get barcode directly from the data-barcode attribute
    const barcode = $trigger.attr("data-barcode").trim().replace(/\s+/g, "");
    const $average = $popup.find(".popup-average");
    const $min = $popup.find(".popup-min");
    const $max = $popup.find(".popup-max");
    const $billsBody = $popup.find(".popup-bills");

    $.ajax({
      type: "GET",
      url: recent_bills_url,
      data: { barcode: barcode },
      success: function (response) {
        if (response.status === "true") {
          $average.text(parseFloat(response.average).toLocaleString("en-IN"));
          $min.text(parseFloat(response.min).toLocaleString("en-IN"));
          $max.text(parseFloat(response.max).toLocaleString("en-IN"));

          // Clear and populate bills
          $billsBody.empty();
          response.bills.forEach(function (bill) {
            $billsBody.append(`
              <tr>
                <td>${bill.invoice__id}</td>
                <td>${bill.invoice__purchasedPerson__name}</td>
                <td>${bill.quantity}</td>
                <td>${bill.price}</td>
              </tr>
            `);
          });

          $trigger.data("loaded", true);
        }
      },
      error: function (error) {
        console.error("Failed to fetch price history:", error);
      },
    });
  }
}

// Validation functions
function validateQuantity(input) {
  const value = parseFloat(input.value);
  if (isNaN(value) || value < 0) {
    input.value = 0;
    CalledToast('error', 'Quantity must be a positive number');
    return false;
  }
  return true;
}

function validatePrice(input) {
  const value = parseFloat(input.value);
  if (isNaN(value) || value < 0) {
    input.value = 0;
    CalledToast('error', 'Price must be a positive number');
    return false;
  }
  return true;
}

// Price display toggle state
let showActualPrice = false;

// Toggle price display function
function togglePriceDisplay() {
  showActualPrice = !showActualPrice;
  const priceCells = $('.mrp');
  const discountCells = $('.discount-value');

  priceCells.each(function () {
    const $cell = $(this);
    const row = $cell.closest('tr');
    const variantSelect = row.find('select[name="size-variants"] option:selected');
    const priceInput = row.find('input[name="price"]');

    if (showActualPrice) {
      // Show actual price
      if (variantSelect.length) {
        const actualPrice = parseFloat(variantSelect.attr('data-amount').replace(/,/g, ''));
        $cell.text(actualPrice.toLocaleString('en-IN'));
        // Only validate price, don't change it
        if (parseFloat(priceInput.val()) < actualPrice) {
          CalledToast('warning', 'Price cannot be less than actual price');
        }
      } else {
        // For non-variant items
        const actualPrice = parseFloat($cell.attr('data-amount').replace(/,/g, ''));
        $cell.text(actualPrice.toLocaleString('en-IN'));
        // Only validate price, don't change it
        if (parseFloat(priceInput.val()) < actualPrice) {
          CalledToast('warning', 'Price cannot be less than actual price');
        }
      }
    } else {
      // Show selling price
      if (variantSelect.length) {
        const sellingPrice = parseFloat(variantSelect.attr('data-selling').replace(/,/g, ''));
        $cell.text(sellingPrice.toLocaleString('en-IN'));
      } else {
        // For non-variant items
        const sellingPrice = parseFloat($cell.attr('data-selling').replace(/,/g, ''));
        $cell.text(sellingPrice.toLocaleString('en-IN'));
      }
    }
  });

  // Toggle between discount and margin
  discountCells.each(function () {
    const $cell = $(this);
    const row = $cell.closest('tr');
    const price = parseFloat(row.find('.mrp').text().replace(/,/g, ''));
    const sellingPrice = parseFloat(row.find('input[name="price"]').val());

    if (showActualPrice) {
      // Calculate margin
      const margin = ((sellingPrice - price) / price * 100).toFixed(2);
      $cell.text(margin);
    } else {
      // Show discount
      const discount = ((price - sellingPrice) / price * 100).toFixed(2);
      $cell.text(discount);
    }
  });

  // Show notification
  CalledToast('info', showActualPrice ? 'Showing Actual Price & Margin' : 'Showing Selling Price & Discount');
}

// Add F9 key event listener
document.addEventListener('keydown', function (event) {
  if (event.key === 'F9') {
    event.preventDefault();
    togglePriceDisplay();
  }
});

// Add price validation on input change
$(document).on('change', 'input[name="price"]', function () {
  const $input = $(this);
  const row = $input.closest('tr');
  const variantSelect = row.find('select[name="size-variants"] option:selected');
  const $cell = row.find('.mrp');

  let actualPrice;
  if (variantSelect.length) {
    actualPrice = parseFloat(variantSelect.attr('data-amount').replace(/,/g, ''));
  } else {
    actualPrice = parseFloat($cell.attr('data-amount').replace(/,/g, ''));
  }

  const enteredPrice = parseFloat($input.val());

  if (enteredPrice < actualPrice) {
    CalledToast('warning', 'Price cannot be less than actual price');
  }
});
