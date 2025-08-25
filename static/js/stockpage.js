$(function () {
  // get autosuggest for main type and subtype
  $.ajax({
    url: stock_suggest_url,
    method: "GET",
    data: {
      suggestion: "both",
    },
    cache: false,
    success: function (response) {
      customAutoComplete($("#id_mainType"), response.list1);
      customAutoComplete($("#id_subType"), response.list2);
    },
  });

  function debounce(func, wait) {
    let timeout;
    return function (...args) {
      const context = this;
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(context, args), wait);
    };
  }

  const debouncedCallMatching = debounce(function () {
    let maintype = $("#id_mainType").val();
    let subtype = $("#id_subType").val();
    let actual_price = $("#id_actual_price").val();

    if (maintype !== "" && (subtype !== "" || actual_price !== "")) {
      callMatching(maintype, subtype, actual_price);
    }
  }, 300); // 300ms delay

  // getting near by stock details
  $("#id_mainType, #id_subType, #id_actual_price").on(
    "keyup",
    debouncedCallMatching
  );

  function callMatching(maintype, subtype, actual_price) {
    // Here, you can send these values to the backend using AJAX or another method
    // and receive matching data in response
    $.ajax({
      url: stock_matching_url,
      method: "GET",
      data: {
        mainType: maintype,
        subType: subtype,
        price: actual_price,
      },
      cache: false,
      success: function (response) {
        const transactionsList = document.getElementById("related_stock");
        transactionsList.innerHTML = "";

        if (response && response.length > 0) {
          response.forEach((transaction) => {
            const transAmount = parseFloat(
              transaction.actual_price
            ).toLocaleString("en-IN", {
              maximumFractionDigits: 2, // Optional: Limit decimal places to 2
            });
            const liElement = document.createElement("h5");
            liElement.textContent = `${transaction.id} - ${transaction.mainType} - ${transaction.subType} - ${transAmount} `;
            transactionsList.appendChild(liElement);
          });
        } else {
          const errorElement = document.createElement("p");
          errorElement.textContent = "No recent data available.";
          transactionsList.appendChild(errorElement);
        }
      },
      error: function () {
        const transactionsList = document.querySelector(".educate-year ul");
        transactionsList.innerHTML = "";

        const errorElement = document.createElement("p");
        errorElement.textContent = "An error occurred while fetching data.";
        transactionsList.appendChild(errorElement);
      },
    });
  }

  // variants  data
  function validateInputs() {
    let isValid = true;

    // Iterate over existing rows
    $("#table_body tr").each(function () {
      const inputs = $(this).find(
        ':input:not([type="checkbox"]):not([type="hidden"])'
      );

      // Check if any non-checkbox and non-hidden input is empty
      for (let i = 0; i < inputs.length; i++) {
        if ($(inputs[i]).val() === "") {
          $(inputs[i]).focus();
          alert("Please fill in all fields before adding a new row.");
          isValid = false;
          return false; // Break out of the loop
        }
      }
    });
    return isValid;
  }

  $("#add_size_form").submit(function (e) {
    e.preventDefault();

    function checkEmptyFields(formSelector) {
      const emptyFields = [];
      $(formSelector)
        .find(":input[required]")
        .each(function () {
          if (!$(this).val().trim()) {
            emptyFields.push($(this).attr("name"));
          }
        });
      return emptyFields;
    }

    const formData = $("#add_size_form").serialize(); // Serialize form data

    const emptyFields = checkEmptyFields("#add_size_form");
    if (emptyFields.length > 0) {
      CalledToast("error", "Please fill out all required fields.");
      const firstEmptyField = $(`[name="${emptyFields[0]}"]`);
      firstEmptyField.focus();
      return; // Stop execution if validation fails
    }

    $.ajax({
      type: "POST",
      url: size_create_url, // Use the constant for the URL
      data: formData,
      success: function (response) {
        if (response.status == 201) {
          CalledToast("info", response.data.name + " Already Existed");
          $("#add_size_form").trigger("reset");
          $(".btn-close").click();
        } else if (response.status == 200) {
          addOptionToAllSelects(response.data.id, response.data.name);
          CalledToast("success", response.data.name + " Created Successfully");
          $("#add_size_form").trigger("reset");
          $(".btn-close").click();
        } else if (response.status == 400) {
          CalledToast("error", "Failed in Adding Size");
        }
      },
      error: function (error) {
        // Handle error
        console.log(error);
      },
    });

    function addOptionToAllSelects(optionValue, optionText) {
      var selects = document.getElementsByClassName("select-options");
      for (var i = 0; i < selects.length; i++) {
        var select = selects[i];
        var option = document.createElement("option");
        option.value = optionValue;
        option.text = optionText;
        select.insertBefore(option, select.options[1]);
      }
    }
  });

  // updating the stock from the row to the form
  function updateStockQuantity() {
    var totalQuantity = 0;

    // Iterate over all size-quantity inputs
    $(".size-quantity").each(function () {
      var quantity = parseFloat($(this).val()) || 0;
      var select = $(this).closest("tr").find("select.select-options"); // Convert to float, default to 0 if not a number

      if (quantity > 0 && select.val() !== "") {
        // Check if quantity is greater than 0 and select is not empty
        totalQuantity += quantity;
      }
    });

    $("#id_quantity").val(totalQuantity);
  }
  // Event delegation for dynamically added size-quantity inputs
  $(document).on("input", ".size-quantity", function () {
    // Update stock quantity whenever a size-quantity input changes
    updateStockQuantity();
  });

  // create a new variant row
  $(document).keydown(function (e) {
    // Check for Ctrl + N
    if (e.altKey && e.key === "n") {
      e.preventDefault(); // Prevent the default browser behavior for Ctrl + N

      // Trigger the click event on #add-variant
      $("#add-variant").click();
    }
  });
});
