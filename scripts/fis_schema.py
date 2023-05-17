from tools import FISenum


class F27(FISenum):
    """
    CNVZSV - Carrier (Ship Via) Master File
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    key_type               = 'An$(1,2)',   0     # Key Group = 'SV'
    carrier_id             = 'An$(3,2)',   1     # Carrier Code
    desc                   = 'Bn$',        2     # Description
    common_carrier         = 'Cn$(1,1)',   3     # Common Carrier (Y/N) ?
    is_this_a_ups_shipment = 'Cn$(2,1)',   4     # Is this a UPS shipment (Y/N) ?
                                                 # (open) Cn$(4,7)
                                                 # (open) Dn$


class F33(FISenum):
    """
    CSMS - CUSTOMER MASTER FILE MAINTENANCE & INQUI
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company_id             = 'An$(1,2)',     0     # Company Code
    cust_id                = 'An$(3,6)',     1     # Customer Code
    key_type               = 'An$(9,1)',     2     # Key Type = BLANK
    name                   = 'Bn$',          3     # Name
    addr1                  = 'Cn$',          4     # Addr Line 1
    addr2                  = 'Dn$',          5     # Addr Line 2
    addr3                  = 'En$',          6     # Addr Line 3 w/zip
    zip_id                 = 'Ln$',          7     # Zip Code
    spec_prices            = 'Fn$(1,1)',     8     # Spec Prices (Y/N)
    price_list_id          = 'Fn$(2,2)',     9     # Price List Code
    cr_status_id           = 'Fn$(4,1)',    10     # Credit Status Code
    cr_to_othr_cust        = 'Fn$(5,1)',    11     # C/R to Othr Cust?
    statements             = 'Fn$(6,1)',    12     # Statements (Y/N)
    delinq_status          = 'Fn$(7,1)',    13     # Delinq Status
    catalog                = 'Fn$(8,1)',    14     # Catalog (Y/N)
    prt_latin_name_yn      = 'Fn$(9,1)',    15     # Prt Latin Name Y/N
    inv_balance            = 'Bn',          16     # Invoice Balance
    unapplied_cash_bal     = 'Cn',          17     # Unapplied Cash Bal
    cr_memo_balance        = 'Dn',          18     # CR Memo Balance
    dr_memo_balance        = 'En',          19     # DR Memo Balance
    cr_limit               = 'Fn',          20     # Credit Limit
    largest_balance        = 'Gn',          21     # Largest Balance
    open_order_amt         = 'Hn',          22     # Open Order Amount
    mtd_sales              = 'In',          23     # M-T-D Sales
    mtd_cost_of_sales      = 'Jn',          24     # M-T-D Cost of Sales
    prev_month_ar          = 'Kn',          25     # Prev Month A/R
    ytd_sales              = 'Ln',          26     # Y-T-D Sales
    ytd_cost_of_sales      = 'Mn',          27     # Y-T-D Cost of Sales
    ytd_crs                = 'Nn',          28     # Y-T-D Credits
    ytd_payments           = 'On',          29     # Y-T-D Payments
    prev_year_sales        = 'Pn',          30     # Prev Year Sales
    taxing_auth_id         = 'Qn$',         31     # Taxing Auth Code
    broker_id              = 'Gn$(1,3)',    32     # Broker Code
    salesrep               = 'Gn$(4,3)',    33     # Salesrep/Brokr Code
    date_lrgst_balnc       = 'Gn$(7,6)',    34     # Date Lrgst Balnc
    date_last_paymt        = 'Gn$(13,6)',   35     # Date Last Paymt
    terms_id               = 'Gn$(19,1)',   36     # Terms Code
    tele                   = 'Gn$(20,10)',  37     # Telephone No.
    service_chg            = 'Gn$(30,1)',   38     # Service Chg (YNM0-9)
    fax_no                 = 'Gn$(31,15)',  39     # Fax Number
    addl_phone_fax         = 'Gn$(46,15)',  40     # Addl Phone/Fax
    resale_no              = 'Gn$(61,15)',  41     # Resale Number
    cust_type              = 'Hn$(1,2)',    42     # Customer Type
    sales_class            = 'Hn$(3,4)',    43     # Sales Class
    price_method           = 'Hn$(7,2)',    44     # Price Method
    promo_allow_cycle      = 'Hn$(9,1)',    45     # Promo Allow Cycle
    key_acct_id            = 'Hn$(10,1)',   46     # Key Account Code
    link_to_ship_to        = 'Hn$(11,2)',   47     # Link to Ship-to
    promo_allow_pct        = 'Hn$(13,5)',   48     # Promo Allow Pct
    alpha_sort_key         = 'In$',         49     # Alpha Sort Key
    date_opened            = 'Jn$(1,6)',    50     # Date Opened
    d_b_rating             = 'Jn$(7,3)',    51     # D&B Rating
    sales_manager          = 'Jn$(10,3)',   52     # Sales Manager
    inv_print_text         = 'Kn$(1,30)',   53     # Invoice Print Text
    contact                = 'Kn$(31,30)',  54     # Acctg Comments
    total_numb_of_invoices = 'Qn',          55     # Total Numb of Invoices
    total_pymt_days        = 'Rn',          56     # Total Payment Days
    cust_rank              = 'Sn',          57     # Customer Rank


class F34(FISenum):
    """
    CSMSS - CUSTOMER MASTER FILE - ADDTN'L SHIP-TO'S
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company               = 'An$(1,2)',     0     # COMPANY
    cust_no               = 'An$(3,6)',     1     # CUSTOMER NUMBER
    key_type              = 'An$(9,1)',     2     # KEY TYPE = "1"
    ship_to_no            = 'An$(10,2)',    3     # SHIP TO NUMBER
    name                  = 'Bn$',          4     # SHIP TO NAME
    addr1                 = 'Cn$',          5     # ADDRESS LINE 1
    addr2                 = 'Dn$',          6     # ADDRESS LINE 2
    addr3                 = 'En$',          7     # ADDRESS LINE 3
    zip_id                = 'Ln$',          8     # ZIP CODE
    master_cust_no        = 'Fn$(1,6)',     9     # MASTER CUSTOMER NO.
                                                  # (OPEN) Fn$(7,2)
    order_print_msg       = 'Fn$(9,2)',    11     # ORDER PRINT MSG
    inv_print_msg         = 'Fn$(11,2)',   12     # INVOICE PRINT MSG
    operator_message      = 'Fn$(13,2)',   13     # OPERATOR MESSAGE
    contact_frequency     = 'Fn$(15,1)',   14     # CONTACT FREQUENCY
                                                  # (OPEN) Fn$(16,1)
    day_contacted         = 'Fn$(17,1)',   16     # DAY CONTACTED
    last_order_date       = 'Fn$(18,6)',   17     # LAST ORDER DATE
    last_inv_date         = 'Fn$(24,6)',   18     # LAST INVOICE DATE
    date_exptd_order      = 'Fn$(30,6)',   19     # DATE EXPTD ORDER
    last_order_no         = 'Fn$(36,6)',   20     # LAST ORDER NUMBER
    last_inv_no           = 'Fn$(42,6)',   21     # LAST INVOICE NO.
    sales_clerk           = 'Fn$(48,3)',   22     # SALES CLERK
    shipping_warehouse    = 'Fn$(51,4)',   23     # SHIPPING WAREHOUSE
    broker_id             = 'Fn$(55,3)',   24     # BROKER CODE
    carrier               = 'Fn$(58,2)',   25     # CARRIER
    route                 = 'Fn$(60,2)',   26     # ROUTE
    stop_no               = 'Fn$(62,2)',   27     # STOP NUMBER
    tax_auth              = 'Fn$(64,2)',   28     # TAX AUTH
    freight_zone          = 'Fn$(66,3)',   29     # Freight Zone
    fob_id                = 'Fn$(69,2)',   30     # FOB CODE
    prepaid_collect       = 'Fn$(71,1)',   31     # Prepaid/Collect(P/C)
    catalog               = 'Fn$(72,1)',   32     # Catalog (Y/N)
    territory_id          = 'Fn$(73,3)',   33     # Territory Code
    sales_rep_broker_id   = 'Fn$(76,3)',   34     # Sales Rep/Broker Code
    destination_warehouse = 'Fn$(79,4)',   35     # Destination Warehouse
                                                  # (open) Fn$(83,8)
    temp_ar               = 'Bn',          37     # Temp A/R $
    order_frequency       = 'Cn',          38     # Order Frequency
    min_order_weight      = 'Dn',          39     # Min Order Weight
    weight_last_order     = 'En',          40     # Weight Last Order
    ttl_order_weight      = 'Fn',          41     # Ttl Order Weight
    total_orders          = 'Gn',          42     # Total # Orders
                                                  # (open) Hn
                                                  # (open) In
                                                  # (open) Jn
                                                  # (open) Kn
                                                  # (open) Ln
                                                  # (open) Mn
                                                  # (open) Nn
                                                  # (open) On
                                                  # (open) Pn
    tele                  = 'Qn$(1,15)',   52     # Phone Number
    fax_no                = 'Qn$(16,15)',  53     # Fax Number
    telex_no              = 'Qn$(31,15)',  54     # Telex Number
    comments              = 'Gn$',         55     # Comments


class F65(FISenum):
    """
    VNMS - VENDOR MASTER FILE MAINT & INQUIRY
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company_id              = 'An$(1,2)',     0     # Company Code
    vendor_id               = 'An$(3,6)',     1     # Vendor Code
    name                    = 'Bn$',          2     # Vendor Name
    addr1                   = 'Cn$',          3     # Address Line 1
    addr2                   = 'Dn$',          4     # Address Line 2
    addr3                   = 'En$',          5     # Address Line 3
    vendor_acct_balance     = 'An',           6     # Vendor Account Balance
    tele                    = 'Gn$(1,15)',    7     # Telephone Number
    fax_no                  = 'Gn$(16,15)',   8     # FAX Number
    telex_no                = 'Gn$(31,15)',   9     # Telex Number
    date_opened             = 'Hn$',         10     # Date Opened
    cur_yr_invoices         = 'Bn',          11     # Cur YR Invoices
    cur_yr_discounts_avail  = 'Cn',          12     # Cur YR Discounts Avail
    cur_yr_discounts_taken  = 'Dn',          13     # Cur YR Discounts Taken
    prev_yr_invoices        = 'En',          14     # Prev YR Invoices
    prev_yr_discnts_avail   = 'Fn',          15     # Prev YR Discnts Avail.
    prev_yr_discnts_taken   = 'Gn',          16     # Prev YR Discnts Taken
    any_contracts           = 'In$(1,1)',    17     # Any Contracts (Y/N)
    fob                     = 'In$(2,2)',    18     # F.O.B. (for purchasing)
    terms_code              = 'In$(4,1)',    19     # Terms Code (for purchasing)
    is_this_a_broker        = 'In$(5,1)',    20     # Is this a Broker (Y/N)
    salesrep_broker_id      = 'In$(6,3)',    21     # Salesrep/Broker Code
    gl_category_for_expense = 'In$(9,1)',    22     # G/L Category for Expense (0,1)
    fed_1099_id_no          = 'In$(10,15)',  23     # 1099 Federal ID number
    pymt_terms              = 'Jn$',         24     # Payment Terms (PP/DDD)
    date_last_purchase      = 'Kn$',         25     # Date Last Purchase
    alphabetic_sort_key     = 'Ln$',         26     # Alphabetic Sort Key
    fed_1099_ytd_balance    = 'Hn',          27     # 1099 YTD Balance
    payee                   = 'Mn$',         28     # Payee (if different)
    contact_name            = 'Nn$',         29     # Contact Name
    standard_gl_acct        = 'On$',         30     # Standard G/L Account


class F74(FISenum):
    """
    EMP1 - P/R EMPLOYEE MASTER BASIC RECORD MAINT/INQUIRY
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company_id        = 'An$(1,2)',    0     # COMPANY CODE
    employee_no       = 'An$(3,5)',    1     # EMPLOYEE NO.
    name              = 'Bn$',         2     # EMPLOYEE NAME
    addr1             = 'Cn$',         3     # ADDRESS 1
    addr2             = 'Dn$',         4     # ADDRESS 2
    addr3             = 'En$',         5     # ADDRESS 3
    socsecno          = 'Fn$',         6     # SOC.SEC.NO.
    tel_no            = 'Gn$',         7     # TELEPHONE NO.
    alpha_sort_key    = 'Hn$',         8     # ALPHA SORT KEY
    date_hired        = 'In$(1,6)',    9     # DATE HIRED
    date_terminated   = 'In$(7,6)',   10     # DATE TERMINATED
    seniority_date    = 'In$(13,6)',  11     # SENIORITY DATE
    birthdate         = 'In$(19,6)',  12     # BIRTHDATE
    last_period_wkd   = 'In$(25,6)',  13     # LAST PERIOD WKD
    hour_1400_date    = 'In$(31,6)',  14     # 1400 HOUR DATE
    pension_eligibil  = 'In$(37,6)',  15     # PENSION ELIGIBIL
    home_dept         = 'Jn$(1,2)',   16     # HOME DEPARTMENT
    home_cost_ctr     = 'Jn$(3,3)',   17     # HOME COST CENTER
    normal_shift      = 'Jn$(6,2)',   18     # NORMAL SHIFT
    contract_no       = 'Jn$(8,6)',   19     # CONTRACT NUMBER
    status_flag       = 'Kn$(1,1)',   20     # STATUS FLAG
    pay_type          = 'Kn$(2,1)',   21     # PAY TYPE
    pay_cycle         = 'Kn$(3,1)',   22     # PAY CYCLE
    marital_status    = 'Kn$(4,1)',   23     # MARITAL STATUS
    fica_exempt       = 'Kn$(5,1)',   24     # FICA EXEMPT
    local_resident    = 'Kn$(6,1)',   25     # LOCAL RESIDENT
    reason_terminated = 'Kn$(7,1)',   26     # REASON TERMINATED
    pension_status    = 'Kn$(8,1)',   27     # PENSION STATUS
    state_tax_abbr    = 'Kn$(9,2)',   28     # STATE TAX ABBR
    local_tax_id      = 'Kn$(11,2)',  29     # LOCAL TAX CODE
    union_id          = 'Kn$(13,3)',  30     # UNION CODE
    worker_s_comp_id  = 'Kn$(16,5)',  31     # WORKER'S COMP CODE
    sex_id            = 'Kn$(21,1)',  32     # SEX CODE
    eic_flag          = 'Kn$(22,2)',  33     # E.I.C. FLAG
    security_flag     = 'Kn$(24,2)',  34     # SECURITY FLAG
    holiday_pay       = 'Kn$(25,1)',  35     # HOLIDAY PAY? (Y/N)
    exempt_fed        = 'X(0)',       36     # # EXEMPT-FED
    exempt_state      = 'X(1)',       37     # # EXEMPT-STATE
    exempt_local      = 'X(2)',       38     # # EXEMPT-LOCAL
    hourly_rate       = 'R(0)',       39     # HOURLY RATE
    salary_rate       = 'R(1)',       40     # SALARY RATE
    qtd_gross         = 'Q(0)',       41     # QTD - GROSS
    qtd_fed_tax       = 'Q(1)',       42     # QTD - FED TAX
    qtd_fica          = 'Q(2)',       43     # QTD - FICA
    qtd_ste_tax       = 'Q(3)',       44     # QTD - STE TAX
    qtd_loc_tax       = 'Q(4)',       45     # QTD - LOC TAX
    qtd_sdi           = 'Q(5)',       46     # QTD - SDI
    qtd_sick_pay      = 'Q(6)',       47     # QTD - SICK PAY
    qtd_eic           = 'Q(7)',       48     # QTD - E.I.C.
    qtd_non_txbl      = 'Q(8)',       49     # QTD - NON TXBL
    qtd_weeks_wrkd    = 'Q(9)',       50     # QTD - # WEEKS WRKD


class F122(FISenum):
    """
    CNVZc - PRODUCT CATEGORY MASTER FILE MAINTENANCE & INQUIRY
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    key_type        = 'An$(1,1)',   0     # KEY TYPE = 'c'
    company_id      = 'An$(2,2)',   1     # COMPANY CODE
    prod_category   = 'An$(4,1)',   2     # PRODUCT CATEGORY
    desc            = 'Bn$',        3     # DESCRIPTION
    gl_id           = 'Cn$',        4     # G/L CODE
    lic_fee_rpt_col = 'Dn$(1,1)',   5     # LIC FEE RPT COL
                                          # (open) Dn$(2,9)

class F135(FISenum):
    """
    NVTY - INVENTORY MASTER FILE MAINTENANCE & INQU
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company_id              = 'An$(1,2)',     0     # Company Code
    item_id                 = 'An$(3,8)',     1     # Item Code
                                                    # (open) An$(11,4)
    warehouse_no            = 'An$(15,4)',    3     # Warehouse Code
    record_type_1           = 'An$(19,3)',    4     # Record Type = '1**'
    available               = 'Bn$(1,1)',     5     # Available (Y/N/D/H)
                                                    # (open) Bn$(2,1)
    saroni_access           = 'Bn$(3,1)',     7     # Saroni Access
    prod_category           = 'Bn$(4,1)',     8     # Product Category
    gl_category             = 'Bn$(5,1)',     9     # G/L Category
    whse_category           = 'Bn$(6,1)',    10     # Whse Category
    selling_units           = 'Bn$(7,2)',    11     # Selling Units
    pricing_units           = 'Bn$(9,2)',    12     # Pricing Units
    message_pricing         = 'Bn$(11,2)',   13     # Message-Pricing
    qty_disc_table_to_use   = 'Bn$(13,2)',   14     # Qty Disc Table to use
    item_type               = 'Bn$(15,1)',   15     # Item Type(I/P/K)
    message_operator        = 'Bn$(16,2)',   16     # Message-Operator
    message_ordr_prt        = 'Bn$(18,2)',   17     # Message-Ordr Prt
    message_po_print        = 'Bn$(20,2)',   18     # Message-P/O Print
    message_inv_prt         = 'Bn$(22,2)',   19     # Message-Invoice Prt
    contracts               = 'Bn$(24,1)',   20     # Contracts(Y/N)
    lot_control             = 'Bn$(25,1)',   21     # Lot Control(YNIL)
    lot_history             = 'Bn$(26,1)',   22     # Lot History(Y/N)
    subsititutes            = 'Bn$(27,1)',   23     # Subsititutes(Y/N)
    other_pckging           = 'Bn$(28,1)',   24     # Other Pckging(Y/N)
    pkgs_used_by_prdctn     = 'Bn$(29,1)',   25     # Pkgs used by Prdctn(Y/N)
    phys_ity_cycle_id       = 'Bn$(30,1)',   26     # Phys Ity Cycle Code
    commodity_id            = 'Bn$(31,3)',   27     # Commodity Code
    bin_location            = 'Bn$(34,6)',   28     # Bin Location
    old_new_item_id         = 'Bn$(40,8)',   29     # Old/New Item Code
    catch_weight            = 'Bn$(48,1)',   30     # Catch Weight(Y/N)
                                                    # (open) Bn$(49,1)
    desc                    = 'Cn$',         32     # Description
    formula_id              = 'Dn$(1,6)',    33     # Formula Code
    label_item_id           = 'Dn$(7,8)',    34     # Label Item Code
    fiber_item_id           = 'Dn$(15,8)',   35     # Fiber Item Code
    size_id                 = 'Dn$(23,3)',   36     # Size Code
    fiber_per_unit          = 'Dn$(26,7)',   37     # Fiber per Unit
    latin_name              = 'Dn$(33,40)',  38     # Latin Name
    public_whse_lot_no      = 'Dn$(73,8)',   39     # Public Whse Lot No.
    gl_acct_sales           = 'En$',         40     # G/L Acct-Sales
    date_avail_discontinued = 'Fn$(1,6)',    41     # Date Avail/Discontinued
    last_physical_count     = 'Fn$(7,6)',    42     # - Last Physical Count
    last_adj                = 'Fn$(13,6)',   43     # - Last Adjustment
    last_shipment           = 'Fn$(19,6)',   44     # - Last Shipment
    last_prdctn_receipt     = 'Fn$(25,6)',   45     # - Last Prdctn/Receipt
    re_order_point_hit      = 'Fn$(31,6)',   46     # - Re-order Point Hit
    last_cost_change        = 'Fn$(37,6)',   47     # - Last Cost Change
    supplier_id             = 'Gn$',         48     # Supplier Code
    unit_net_weight         = 'I(0)',        49     # Unit Net Weight
    unit_gross_weight       = 'I(1)',        50     # Unit Gross Weight
    unit_cube               = 'I(2)',        51     # Unit Cube
    shelf_life              = 'I(3)',        52     # Shelf Life (Days)
    re_order_point          = 'I(4)',        53     # Re-Order Point
    maximum_stock_level     = 'I(5)',        54     # Maximum Stock Level
    qty_on_hand             = 'I(6)',        55     # Quantity on hand
    qty_committed           = 'I(7)',        56     # Quantity Committed
    qty_on_order            = 'I(8)',        57     # Quantity on order
    unit_cost_gross         = 'I(9)',        58     # Unit Cost - Gross
    unit_cost_replacmt      = 'I(10)',       59     # Unit cost - Replacmt
    unit_cost_net           = 'I(11)',       60     # Unit Cost - Net
    alt_unit_cvt_factor     = 'I(12)',       61     # Alt Unit Cvt Factor
    unit_cost_frt           = 'I(13)',       62     # Unit Cost - Frt
    unit_cost_hndlg         = 'I(14)',       63     # Unit Cost - Hndlg
    labels_per_unit         = 'I(15)',       64     # Labels per unit
    qty_last_phys_count     = 'I(16)',       65     # Qty Last Phys Count
    starting_qty            = 'I(17)',       66     # Starting Qty (Stk Mvmt)
    qty_end_of_period       = 'I(18)',       67     # Qty End of Period(Stk Mvmt)
    last_month_unit_sales   = 'I(19)',       68     # Last Month Unit Sales
    ytd_unit_sales          = 'I(20)',       69     # YTD Unit Sales
    label_allow_per_unit    = 'I(21)',       70     # Label Allow per Unit
    total_catch_weight      = 'I(22)',       71     # Total Catch Weight
    contract_balance        = 'I(23)',       72     # Contract Balance
                                                    # (open) I(24)
                                                    # (open) I(25)


class F140(FISenum):
    """
    CSMSB - CUSTOMER MASTER FILE - DEFAULT SHIP-TO
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company               = 'An$(1,2)',     0     # COMPANY
    cust_id               = 'An$(3,6)',     1     # Customer Code
    key_type              = 'An$(9,1)',     2     # KEY GROUP = '1'
    ship_to_code_spaces   = 'An$(10,2)',    3     # Ship-to Code=spaces
    name                  = 'Bn$',          4     # SHIP TO NAME
    addr1                 = 'Cn$',          5     # ADDRESS LINE 1
    addr2                 = 'Dn$',          6     # ADDRESS LINE 2
    addr3                 = 'En$',          7     # ADDRESS LINE 3
    zip_id                = 'Ln$',          8     # ZIP CODE
    master_cust_no        = 'Fn$(1,6)',     9     # MASTER CUSTOMER NO.
                                                  # (OPEN) Fn$(7,2)
    order_print_msg       = 'Fn$(9,2)',    11     # ORDER PRINT MSG
    inv_print_msg         = 'Fn$(11,2)',   12     # INVOICE PRINT MSG
    operator_message      = 'Fn$(13,2)',   13     # OPERATOR MESSAGE
    contact_frequency     = 'Fn$(15,1)',   14     # CONTACT FREQUENCY
                                                  # (OPEN) Fn$(16,1)
    day_contacted         = 'Fn$(17,1)',   16     # DAY CONTACTED
    last_order_date       = 'Fn$(18,6)',   17     # LAST ORDER DATE
    last_inv_date         = 'Fn$(24,6)',   18     # LAST INVOICE DATE
    date_exptd_order      = 'Fn$(30,6)',   19     # DATE EXPTD ORDER
    last_order_no         = 'Fn$(36,6)',   20     # LAST ORDER NUMBER
    last_inv_no           = 'Fn$(42,6)',   21     # LAST INVOICE NO.
    sales_clerk           = 'Fn$(48,3)',   22     # SALES CLERK
    shipping_warehouse    = 'Fn$(51,4)',   23     # SHIPPING WAREHOUSE
    broker_id             = 'Fn$(55,3)',   24     # BROKER CODE
    carrier               = 'Fn$(58,2)',   25     # CARRIER
    route                 = 'Fn$(60,2)',   26     # ROUTE
    stop_no               = 'Fn$(62,2)',   27     # STOP NUMBER
    tax_auth              = 'Fn$(64,2)',   28     # TAX AUTH
    freight_zone          = 'Fn$(66,3)',   29     # Freight Zone
    fob_id                = 'Fn$(69,2)',   30     # FOB CODE
    prepaid_collect       = 'Fn$(71,1)',   31     # Prepaid/Collect(P/C)
    catalog               = 'Fn$(72,1)',   32     # Catalog (Y/N)
    territory_id          = 'Fn$(73,3)',   33     # Territory Code
    sales_rep_broker_id   = 'Fn$(76,3)',   34     # Sales Rep/Broker Code
    destination_warehouse = 'Fn$(79,4)',   35     # Destination Warehouse
                                                  # (open) Fn$(83,8)
    temp_ar               = 'Bn',          37     # Temp A/R $
    order_frequency       = 'Cn',          38     # Order Frequency
    min_order_weight      = 'Dn',          39     # Min Order Weight
    weight_last_order     = 'En',          40     # Weight Last Order
    ttl_order_weight      = 'Fn',          41     # Ttl Order Weight
    total_orders          = 'Gn',          42     # Total # Orders
                                                  # (open) Hn
                                                  # (open) In
                                                  # (open) Jn
                                                  # (open) Kn
                                                  # (open) Ln
                                                  # (open) Mn
                                                  # (open) Nn
                                                  # (open) On
                                                  # (open) Pn
    tele                  = 'Qn$(1,15)',   52     # Phone Number
    fax_no                = 'Qn$(16,15)',  53     # Fax Number
    telex_no              = 'Qn$(31,15)',  54     # Telex Number
    comments              = 'Gn$',         55     # Comments


class F163(FISenum):
    """
    POSM - SUPPLIER MASTER FILE
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company_id        = 'An$(1,2)',     0     # COMPANY CODE
    supplier_no       = 'An$(3,6)',     1     # SUPPLIER NUMBER
    name              = 'Bn$',          2     # SUPPLIER NAME
    addr1             = 'Cn$',          3     # ADDRESS 1
    addr2             = 'Dn$',          4     # ADDRESS 2
    addr3             = 'En$',          5     # ADDRESS 3
                                              # (open) An
    tele              = 'Gn$(1,15)',    7     # Telephone Number
    fax_no            = 'Gn$(16,15)',   8     # FAX Number
    telex_no          = 'Gn$(31,15)',   9     # Telex Number
                                              # (open) Hn$
                                              # (open) Bn
                                              # (open) Cn
                                              # (open) Dn
                                              # (open) En
                                              # (open) Fn
                                              # (open) Gn
    contracts         = 'In$(1,1)',    17     # CONTRACTS? (Y/N)
    fob_id            = 'In$(2,2)',    18     # FOB CODE
    terms_id          = 'In$(4,1)',    19     # TERMS CODE
                                              # (open) In$(5,1)
                                              # (open) In$(6,3)
                                              # (open) In$(9,1)
    vendor_no         = 'In$(10,6)',   23     # VENDOR NUMBER
                                              # (open) In$(16,9)
                                              # (open) Jn$
    date_last_receipt = 'Kn$',         26     # DATE LAST RECEIPT
    sort_key          = 'Ln$',         27     # SORT KEY
                                              # (open) Hn
                                              # (open) Mn$
                                              # (open) Nn$
                                              # (open) On$


class F250(FISenum):
    """
    NVBA - INVENTORY LOT CONTROL FILE MAINTENANCE &
    """
    #
    _init_ = "value sequence"
    _order_ = lambda m: m.sequence
    #
    company_id               = 'An$(1,2)',     0     # Company Code
    item_id                  = 'An$(3,8)',     1     # Item Code
                                                     # (open) An$(11,4)
    warehouse_id             = 'An$(15,4)',    3     # Warehouse Code
    lot_no                   = 'An$(19,8)',    4     # Lot Number
    prod_receipt_date        = 'Bn$(1,6)',     5     # Production/Receipt Date
    hold_date                = 'Bn$(7,6)',     6     # Hold Date
                                                     # (open) Bn$(13,6)
    tag_type_id              = 'Cn$(1,2)',     8     # Tag Type Code
    random_weights           = 'Cn$(3,1)',     9     # Random Weights (Y,sp=no)
    pack_type                = 'Cn$(4,2)',    10     # Pack Type
    status_code              = 'Cn$(6,1)',    11     # Status Code (sp/H/C)
    hold_reason_id           = 'Cn$(7,2)',    12     # Hold Reason Code
    location                 = 'Cn$(9,2)',    13     # Location
    comments_part_1          = 'Cn$(11,20)',  14     # Comments Part 1
    reference_no             = 'Cn$(31,8)',   15     # Reference Number
    bin_no                   = 'Cn$(39,6)',   16     # Bin Number
    publ_whse_lot_no         = 'Cn$(44,15)',  17     # Publ Whse Lot No
    comments_part_2          = 'Cn$(59,30)',  18     # Comments Part 2
    qty_on_hand              = 'Q(0)',        19     # Quantity on Hand
    qty_committed            = 'Q(1)',        20     # Quantity Committed
    qty_on_order             = 'Q(2)',        21     # Quantity on Order
    standard_lot_cost        = 'Q(3)',        22     # Standard Lot Cost
    qty_produced             = 'Q(4)',        23     # Quantity Produced
    qty_on_hold              = 'Q(5)',        24     # Quantity on Hold
    standard_pack_in_lbs     = 'Q(6)',        25     # Standard Pack in Lbs
    piece_count              = 'Q(7)',        26     # Piece Count
    total_net_weight_on_hand = 'Q(8)',        27     # Total Net Weight on Hand
    beg_bal                  = 'Q(9)',        28     # Beg Bal (temp)
    net_movement             = 'Q(10)',       29     # Net movement(temp)


