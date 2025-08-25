// Stock Invoice Summary JavaScript
$(document).ready(function () {

    // Function to calculate supplier summary
    function calculateSupplierSummary(data) {
        const supplierSummary = {};

        data.forEach(item => {
            const supplier = item.supplier_name;
            const percentage = parseFloat(item.sold_percentage) || 0;
            const invoiceAmount = parseFloat(item.invoice_amount) || 0;
            const presentAmount = parseFloat(item.present_amount) || 0;

            if (!supplierSummary[supplier]) {
                supplierSummary[supplier] = {
                    totalInvoices: 0,
                    totalPercentage: 0,
                    totalInvoiceAmount: 0,
                    totalPresentAmount: 0
                };
            }

            supplierSummary[supplier].totalInvoices++;
            supplierSummary[supplier].totalPercentage += percentage;
            supplierSummary[supplier].totalInvoiceAmount += invoiceAmount;
            supplierSummary[supplier].totalPresentAmount += presentAmount;
        });

        // Calculate averages and format data
        const summaryData = Object.keys(supplierSummary).map(supplier => {
            const data = supplierSummary[supplier];
            return {
                supplier: supplier,
                totalInvoices: data.totalInvoices,
                averagePercentage: data.totalInvoices > 0 ? (data.totalPercentage / data.totalInvoices).toFixed(2) : 0,
                totalInvoiceAmount: data.totalInvoiceAmount.toFixed(2),
                totalPresentAmount: data.totalPresentAmount.toFixed(2)
            };
        });

        return summaryData;
    }

    // Function to format currency
    function formatCurrency(amount) {
        return parseFloat(amount).toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // Function to update summary table
    function updateSummaryTable(summaryData) {
        const summaryBody = $('#summary_table_body');

        if (summaryData.length === 0) {
            summaryBody.html('<tr><td colspan="5" class="text-center">No data available</td></tr>');
            return;
        }

        let html = '';
        summaryData.forEach(item => {
            const percentageClass = item.averagePercentage > 50 ? 'text-success' :
                item.averagePercentage > 25 ? 'text-warning' : 'text-danger';

            html += `
        <tr>
          <td><strong>${item.supplier}</strong></td>
          <td>${item.totalInvoices}</td>
          <td class="${percentageClass}"><strong>${item.averagePercentage}%</strong></td>
          <td>${formatCurrency(item.totalInvoiceAmount)}</td>
          <td>${formatCurrency(item.totalPresentAmount)}</td>
        </tr>
      `;
        });

        summaryBody.html(html);
    }

    // Function to extract data from table and update summary
    function updateSummaryFromTable() {
        const tableData = [];
        $('#table_body tr').each(function () {
            const row = $(this);
            const cells = row.find('td');

            if (cells.length >= 8) {
                const supplier = cells.eq(1).text().trim();
                const invoiceAmount = cells.eq(3).text().replace(/[^\d.]/g, '');
                const totalAmount = cells.eq(5).text().replace(/[^\d.]/g, '');
                const presentAmount = cells.eq(6).text().replace(/[^\d.]/g, '');
                const percentage = cells.eq(7).text().replace(/[^\d.]/g, '');

                if (supplier && supplier !== 'No data found.') {
                    tableData.push({
                        supplier_name: supplier,
                        invoice_amount: invoiceAmount,
                        total_amount: totalAmount,
                        present_amount: presentAmount,
                        sold_percentage: percentage
                    });
                }
            }
        });

        // Calculate and display summary
        const summaryData = calculateSupplierSummary(tableData);
        updateSummaryTable(summaryData);
    }

    // Summary table sorting functionality
    function initializeSorting() {
        let currentSort = { column: null, direction: 'asc' };

        $('.sortable').on('click', function () {
            const column = $(this).data('sort');
            const direction = (currentSort.column === column && currentSort.direction === 'asc') ? 'desc' : 'asc';

            // Update sort state
            currentSort = { column, direction };

            // Update sort icons
            $('.sortable i').removeClass('fa-sort-up fa-sort-down').addClass('fa-sort');
            const icon = $(this).find('i');
            icon.removeClass('fa-sort').addClass(direction === 'asc' ? 'fa-sort-up' : 'fa-sort-down');

            // Sort the table
            sortSummaryTable(column, direction);
        });
    }

    function sortSummaryTable(column, direction) {
        const tbody = $('#summary_table_body');
        const rows = tbody.find('tr').toArray();

        // Don't sort if it's the "No data available" row
        if (rows.length === 1 && $(rows[0]).find('td').length === 1) {
            return;
        }

        rows.sort(function (a, b) {
            let aVal, bVal;

            switch (column) {
                case 'supplier':
                    aVal = $(a).find('td:eq(0)').text().trim();
                    bVal = $(b).find('td:eq(0)').text().trim();
                    break;
                case 'invoices':
                    aVal = parseInt($(a).find('td:eq(1)').text().trim()) || 0;
                    bVal = parseInt($(b).find('td:eq(1)').text().trim()) || 0;
                    break;
                case 'percentage':
                    aVal = parseFloat($(a).find('td:eq(2)').text().replace('%', '').trim()) || 0;
                    bVal = parseFloat($(b).find('td:eq(2)').text().replace('%', '').trim()) || 0;
                    break;
                case 'invoiceAmount':
                    aVal = parseFloat($(a).find('td:eq(3)').text().replace(/,/g, '').trim()) || 0;
                    bVal = parseFloat($(b).find('td:eq(3)').text().replace(/,/g, '').trim()) || 0;
                    break;
                case 'presentAmount':
                    aVal = parseFloat($(a).find('td:eq(4)').text().replace(/,/g, '').trim()) || 0;
                    bVal = parseFloat($(b).find('td:eq(4)').text().replace(/,/g, '').trim()) || 0;
                    break;
                default:
                    return 0;
            }

            if (direction === 'asc') {
                return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
            } else {
                return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
            }
        });

        // Re-append sorted rows
        tbody.empty();
        rows.forEach(function (row) {
            tbody.append(row);
        });
    }

    // Initialize everything
    function initialize() {
        initializeSorting();

        // Wait for initial data to load, then update summary
        setTimeout(function () {
            updateSummaryFromTable();
        }, 1000);

        // Monitor for changes in the table body
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === 'childList' && mutation.target.id === 'table_body') {
                    // Table content changed, update summary
                    setTimeout(function () {
                        updateSummaryFromTable();
                    }, 100);
                }
            });
        });

        // Start observing the table body
        const tableBody = document.getElementById('table_body');
        if (tableBody) {
            observer.observe(tableBody, { childList: true, subtree: true });
        }
    }

    // Start initialization
    initialize();
}); 