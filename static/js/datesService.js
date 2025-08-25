class DatesService {
  constructor(options = {}) {
    this.state = {
      filterType: "Today",
      startDate: null,
      endDate: null,
    };
    
    // Default options that can be overridden
    this.options = {
      tableBodySelector: "#table_body",
      dateButtonSelector: ".date-btn",
      submitButtonSelector: "#submitButton",
      startDateSelector: "#startDateInput",
      endDateSelector: "#endDateInput",
      pdfButtonSelector: "#dow_pdf",
      excelButtonSelector: "#dow_excel",
      onSuccess: null,
      urls: {
        fetch: null,
        pdf: null,
        excel: null
      },
      features: {
        pdf: false,
        excel: false
      },
      ...options
    };

    this.initializeFeatures();
  }

  initializeFeatures() {
    // Only bind PDF events if URL is provided
    if (this.options.urls.pdf) {
      this.options.features.pdf = true;
      $(this.options.pdfButtonSelector).show();
    } else {
      $(this.options.pdfButtonSelector).hide();
    }

    // Only bind Excel events if URL is provided
    if (this.options.urls.excel) {
      this.options.features.excel = true;
      $(this.options.excelButtonSelector).show();
    } else {
      $(this.options.excelButtonSelector).hide();
    }
  }

  init() {
    if (!this.options.urls.fetch) {
      console.error("Fetch URL is required");
      return;
    }
    
    this.bindEvents();
    return this.fetchInvoiceData();
  }

  bindEvents() {
    // Bind date filter events
    $(this.options.dateButtonSelector).click((e) => {
      this.state.filterType = $(e.currentTarget).data("date");
      this.state.startDate = null;
      this.state.endDate = null;
      this.fetchInvoiceData();
    });

    $(this.options.submitButtonSelector).click(() => {
      const startDate = $(this.options.startDateSelector).val();
      const endDate = $(this.options.endDateSelector).val();

      if (startDate && endDate) {
        this.state.filterType = "custom";
        this.state.startDate = startDate;
        this.state.endDate = endDate;
        this.fetchInvoiceData();
      }
    });

    // Bind export buttons if features are enabled
    if (this.options.features.pdf) {
      $(this.options.pdfButtonSelector).click(() => this.downloadReport("pdf"));
    }

    if (this.options.features.excel) {
      $(this.options.excelButtonSelector).click(() => this.downloadReport("excel"));
    }
  }

  fetchInvoiceData() {
    const params = {
      type_of: this.state.filterType,
      ...(this.state.filterType === "custom" && {
        from_date: this.state.startDate,
        to_date: this.state.endDate,
      }),
    };

    return $.ajax({
      url: this.options.urls.fetch,
      method: "GET",
      data: params,
      success: (response) => {
        if (this.options.onSuccess) {
          this.options.onSuccess(response, this.state);
        } else {
          $(this.options.tableBodySelector).empty().append(response);
        }
      },
    });
  }

  downloadReport(type) {
    const url = type === "pdf" ? this.options.urls.pdf : this.options.urls.excel;
    if (!url) {
      console.error(`${type.toUpperCase()} URL not configured`);
      return;
    }

    const params = new URLSearchParams({
      type_of: this.state.filterType,
      ...(this.state.filterType === "custom" && {
        from_date: this.state.startDate || "",
        to_date: this.state.endDate || "",
      }),
    });

    window.open(`${url}?${params.toString()}`, "_blank");
  }

  getState() {
    return { ...this.state };
  }

  setState(newState) {
    this.state = { ...this.state, ...newState };
  }
}

// Export for use in other files
window.DatesService = DatesService;
