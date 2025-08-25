// reportService.js

class ReportService {
  constructor(options = {}) {
    this.state = {
      reportType: "This Month",
      startDate: null,
      endDate: null,
    };

    // Default options that can be overridden
    this.options = {
      // Selectors
      reportSelectSelector: "#reportSelect",
      reportDatesSelector: "#reportDates",
      startDateSelector: "#startDateInput",
      endDateSelector: "#endDateInput",
      pdfButtonSelector: "#pdfReport",
      excelButtonSelector: "#excelReport",

      // Callbacks
      onError: (message) => {
        if (typeof CalledToast === "function") {
          CalledToast("info", message);
        } else {
          console.warn(message);
        }
      },

      // URLs configuration
      urls: {
        pdf: null,
        excel: null,
      },

      // Feature flags
      features: {
        pdf: false,
        excel: false,
      },
      ...options,
    };

    this.initializeFeatures();
  }

  initializeFeatures() {
    // Enable PDF feature if URL is provided
    if (this.options.urls.pdf) {
      this.options.features.pdf = true;
      $(this.options.pdfButtonSelector).show();
    } else {
      $(this.options.pdfButtonSelector).hide();
    }

    // Enable Excel feature if URL is provided
    if (this.options.urls.excel) {
      this.options.features.excel = true;
      $(this.options.excelButtonSelector).show();
    } else {
      $(this.options.excelButtonSelector).hide();
    }
  }

  init() {
    this.bindEvents();
    return this;
  }

  bindEvents() {
    // Handle report type selection
    $(this.options.reportSelectSelector).on("change", (e) => {
      this.state.reportType = $(e.target).val();
      $(this.options.reportDatesSelector).toggle(
        this.state.reportType === "custom"
      );
    });

    // Handle PDF generation
    if (this.options.features.pdf) {
      $(this.options.pdfButtonSelector).on("click", () =>
        this.handleReportGeneration("pdf")
      );
    }

    // Handle Excel generation
    if (this.options.features.excel) {
      $(this.options.excelButtonSelector).on("click", () =>
        this.handleReportGeneration("excel")
      );
    }
  }

  handleReportGeneration(type) {
    try {
      if (this.state.reportType === "custom") {
        const dates = this.validateCustomDates();
        if (!dates) return;

        this.generateReport(type, "custom", dates.startDate, dates.endDate);
      } else {
        this.generateReport(type, this.state.reportType);
      }
    } catch (error) {
      console.error(`Error generating ${type} report:`, error);
      this.options.onError(`Failed to generate ${type} report`);
    }
  }

  validateCustomDates() {
    const startDate = $(this.options.startDateSelector).val();
    const endDate = $(this.options.endDateSelector).val();

    if (!startDate || !endDate) {
      this.options.onError("Please select both start and end dates");
      $(this.options.startDateSelector).focus();
      return null;
    }

    if (new Date(startDate) > new Date(endDate)) {
      this.options.onError("Start date cannot be after end date");
      return null;
    }

    return { startDate, endDate };
  }

  generateReport(type, reportType, startDate = "", endDate = "") {
    const url = this.options.urls[type];
    if (!url) {
      throw new Error(`URL not configured for ${type} report`);
    }

    const params = new URLSearchParams({
      type_of: reportType,
      from_date: startDate,
      to_date: endDate,
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
window.ReportService = ReportService;
