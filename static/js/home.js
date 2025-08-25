$(function () {
  // create the default
  document.addEventListener("keydown", function (event) {
    if (event.ctrlKey && event.key === "F1") {
      url = "/billing/defaultRoom/";
      window.open(url, "_blank");
    }
  });
});

// click notification to get data
$("#InvoiceNotifications").click(function (event) {
  var dropdownMenu = $(this).next(".dropdown-menu.notifications"); // Get the dropdown menu
  if (dropdownMenu.hasClass("show")) {
    event.preventDefault();
    getNotifications();
  }
});

// creates the nofifications
function getNotifications() {
  $.ajax({
    url: "/getNotification/",
    method: "GET",
    success: function (response) {
      $(".notification-list").empty("reset");
      $(".notification-list").append(response);
    },
  });
}

// makes the message to display
const Toast = Swal.mixin({
  toast: true,
  position: "top-end",
  showConfirmButton: false,
  timer: 5000,
  timerProgressBar: true,
  didOpen: (toast) => {
    toast.addEventListener("mouseenter", Swal.stopTimer);
    toast.addEventListener("mouseleave", Swal.resumeTimer);
  },
});

// calls the function to display messages
function CalledToast(type, message) {
  Toast.fire({
    icon: type,
    title: message,
  });
}

// make the suggestion for the input
function customAutoComplete(input, data) {
  input.autocomplete({
    source: JSON.parse(data),
    minLength: 0,
    focus: function (event, ui) {
      event.preventDefault();
    },
    select: function (event, ui) {
      input.val(ui.item.value);
      return false;
    },
  });
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function getRecentTransactions(url, id, model, elementId) {
  const transactionsList = document.querySelector(`#${elementId} ul`);
  transactionsList.innerHTML = "";

  $.ajax({
    url: url,
    method: "GET",
    data: {
      id: id,
      model: model,
    },
    cache: false,
    success: function (response) {
      if (response && response.length > 0) {
        response.forEach((transaction) => {
          const transAmount = parseFloat(transaction.amount).toLocaleString(
            "en-IN",
            {
              maximumFractionDigits: 2, // Optional: Limit decimal places to 2
            }
          );
          const liElement = document.createElement("h5");
          liElement.textContent = `${transaction.date} - ${transAmount} - ${transaction.remarks}`;
          transactionsList.appendChild(liElement);
        });
      } else {
        const errorElement = document.createElement("p");
        errorElement.textContent = "No recent data available.";
        transactionsList.appendChild(errorElement);
      }
    },
    error: function () {
      const errorElement = document.createElement("p");
      errorElement.textContent = "An error occurred while fetching data.";
      transactionsList.appendChild(errorElement);
    },
  });
}

function createModel(id_input, name, model_link) {
  var idModelSelect = document.getElementById(id_input);

  // Find the closest parent div with class 'form-inner'
  var formInnerDiv = idModelSelect.closest(".local-forms");

  // Find the label within the form-inner div
  var label = formInnerDiv.querySelector("label");

  // Create a new link element
  var link = document.createElement("a");
  link.textContent = " - Add " + name;
  link.href = "#";
  link.setAttribute("data-bs-toggle", "modal");
  link.setAttribute("data-bs-target", "#" + model_link);

  // Append the link element as a child of the label element
  label.appendChild(link);
}

function createNewOptions(form_id, create_url, related_input) {
  $(form_id).submit(function (e) {
    e.preventDefault();
    var form = $(this).closest("form");
    var formData = form.serialize();

    $.ajax({
      url: create_url,
      method: "POST",
      data: formData,
      success: function (response) {
        if (response.status === 200) {
          adjustSelectOptions(response.data);
          form[0].reset();
          form.closest(".modal").find(".btn-close").trigger("click");
          // Optional: Show success message
          if (response.message) {
            CalledToast('success', response.message)
          }
        } else {
          // Show error message
          CalledToast('error', response.message)
        }
      },
      error: function (xhr, errmsg, err) {
        CalledToast('error', "Failed to create items")
      }
    });
  });

  function adjustSelectOptions(data) {
    $.each(data, function (index, value) {
      var existingOption = $(related_input).find('option[value="' + value.id + '"]');

      if (existingOption.length === 0) {
        // Add new option if it doesn't exist
        var newOption = new Option(value.name, value.id, true, value.created);
        $(related_input).append(newOption);
      } else if (!value.created) {
        // Select existing option if it was matched
        existingOption.prop("selected", true);
      }
    });
    $(related_input).trigger("change");
  }
}

// Generic popup positioning function
function positionPopup($trigger, $popup) {
  const rect = $trigger[0].getBoundingClientRect();
  const popupHeight = $popup.outerHeight();

  // Calculate position
  let top = rect.top - popupHeight - 10; // 10px gap
  if (top < 0) {
    // If would go above viewport
    top = rect.bottom + 10; // Position below instead
  }
  // Apply position
  $popup.css({
    top: `${top}px`,
    left: `${rect.left + 50}px`,
    behavior: "smooth",
  });
}

function initializePriceCalculations(config) {
  const {
    actualPriceId = '#id_actual_price',
    sellingPriceId = '#id_mrp',
    discountId = '#id_discount',
    discountRateId = '#id_discount_price',
    isNew = false,
    multiplier = 2
  } = config;

  const actual = document.querySelector(actualPriceId);
  const selling = document.querySelector(sellingPriceId);
  const discount = document.querySelector(discountId);
  const discountRate = document.querySelector(discountRateId);

  // Only add doubleAmount listener if it's a new entry
  if (isNew && actual && selling) {
    actual.addEventListener("keyup", () => {
      selling.value = multiplier * actual.value;
    });
  }

  // Add discount calculation listener
  if (discount && selling && discountRate) {
    const calculateDiscount = () => {
      discountRate.value = selling.value - (selling.value * (discount.value / 100));
    };

    discount.addEventListener("keyup", calculateDiscount);
    selling.addEventListener("keyup", calculateDiscount);

    // Initial calculation
    calculateDiscount();
  }
}

// Function to add bubbles to a specific input field
function addBubbles(inputId, bubbleValues) {
  const inputField = document.getElementById(inputId);

  if (!inputField) {
    console.error("Input field not found!");
    return;
  }

  // Remove existing bubble container if any
  const existingContainer = document.getElementById(`bubble-container-${inputId}`);
  if (existingContainer) {
    existingContainer.remove();
  }

  // Create the bubble container div
  const bubbleContainer = document.createElement("div");
  bubbleContainer.id = `bubble-container-${inputId}`;
  bubbleContainer.className = "bubble-container mt-2";

  // Append the bubble container below the input field
  inputField.parentNode.insertBefore(bubbleContainer, inputField.nextSibling);

  // Format number with commas
  const formatNumber = (value) => {
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Create bubbles and add them to the container
  bubbleValues.forEach((value) => {
    const bubble = document.createElement("span");
    bubble.className = "bubble";
    // Display formatted number
    bubble.textContent = formatNumber(value);
    // Store original value as data attribute
    bubble.setAttribute("data-value", value);

    // Add click event to the bubble
    bubble.addEventListener("click", function () {
      // Set the original float value to input
      inputField.value = parseFloat(this.getAttribute("data-value"));

      // Optional: Add active class to the clicked bubble
      document.querySelectorAll(`#bubble-container-${inputId} .bubble`)
        .forEach(b => b.classList.remove("active"));
      bubble.classList.add("active");
    });

    bubbleContainer.appendChild(bubble);
  });
}

function getAmountsSuggestions(amount_url = "", id = null, input_id) {
  // Input validation
  if (!amount_url || !input_id) {
    console.error("URL and input ID are required");
    return;
  }

  $.ajax({
    url: amount_url,
    method: "GET",
    data: { id: id },
    cache: false,
    success: function (response) {
      if (response.amounts && Array.isArray(response.amounts)) {
        addBubbles(input_id, response.amounts);
      } else {
        console.warn("No amounts received from server");
      }
    },
    error: function (xhr, status, error) {
      console.error("Error fetching amounts:", xhr.responseJSON?.error || error);
    },
  });
}