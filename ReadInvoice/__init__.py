from dataclasses import fields
import json, re
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import FormRecognizerClient
#from azure.ai.formrecognizer import DocumentAnalysisClient
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    #logging.info('Python HTTP trigger function processed a request.')

    invoice_uri = req.params.get('uri')
    key = req.params.get('key')
    endpoint = "https://ap-formrecognizer.cognitiveservices.azure.com/"
    
    #keys based on unique keywords in vendor name
    vendor_dict = {
        'AQUA CLEAR': {
            'cust_name_type': 'serv_name',
            'sage_id': 'AQUA CL',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'CARTRIDGE': {
            'cust_name_type': 'ship_name',
            'sage_id': 'CARTRID',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'COZZINI': {
            'cust_name_type': 'ship_name',
            'sage_id': 'COZZINI',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'HOBART': {
            'cust_name_type': 'serv_name',
            'sage_id': 'HOB SER',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'HOLSTON': {
            'cust_name_type': 'cust_name',
            'sage_id': 'HOLSTON',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'J & F MECHANICAL': {
            'cust_name_type': 'bill_name',
            'sage_id': 'J&F MEC',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'NIEDLOV': {
            'cust_name_type': 'ship_name',
            'sage_id': 'NIEDLOV',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'PREPWIZARD': {
            'cust_name_type': 'ship_name',
            'sage_id': 'PREPWIZ',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'DIXIE': {
            'cust_name_type': 'ship_name',
            'sage_id': 'DIXIEPR',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'QUALITY BAKER': {
            'cust_name_type': 'cust_name',
            'sage_id': 'CYBAKE',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'TRITEX': {
            'cust_name_type': 'cust_name',
            'sage_id': 'TRITEX',
            'inv_summarized': False,
            'expect_loc_id': True
        },
        'VIENNA': {
            'cust_name_type': 'ship_name',
            'sage_id': 'VIENNA',
            'inv_summarized': False,
            'expect_loc_id': True,
            'inv_total_field': 'previous_unpaid_balance'
        },
        'WASSERSTROM': {
            'cust_name_type': 'ship_name',
            'sage_id': 'WASSERS',
            'inv_summarized': False,
            'expect_loc_id': False
        },
        'WORLD': {
            'cust_name_type': 'in_table',
            'sage_id': 'WORLDSP',
            'inv_summarized': True,
            'expect_loc_id': True
        }
    }
    
    sage_vendors = {}
    for v in vendor_dict.keys():
        sage_vendors[vendor_dict[v]['sage_id']] = v

    location_dict = {
        '2': {
            'name_key': ['POWELL', '16COOrSY4qqj71p7m', 'AUBPOW', 'EMORY'],
            'addr_key': ['POWELL', 'EMORY']
        },
        '3': {
            'name_key': ['SUNSPOT', 'SUN SPOT'],
            'addr_key': ['SUNSPOT']
        },
        '4': {
            'name_key': ['CEDAR', 'MIDDLEBROOK', '16CVqvSY4r4xF1xH5'],
            'addr_key': ['MIDDLEBROOK', 'CEDAR']
        },
        '5': {
            'name_key': ['MARYVILLE', 'AzqNMmSY4qGKj1rhz', '- MARYVILLE', "AUBREY'S INC."],
            'addr_key': ['- MARYVILLE'],
            'exclude_key': ['BLUETICK', 'BLUMAR', "BARLEY'S MARYVILLE", 'BARLEY']
        },
        '6': {
            'name_key': ['HIXSON', '169lRsSY4rjvz1ulr', 'CHATTANOOGA'],
            'addr_key': ['CHATTANOOGA', 'HIXSON']
        },
        '7': {
            'name_key': ['UT CAMPUS', 'STEFANOS-CUMBERLAND', 'STEFANOS PIZZA', 'CHICAGO'],
            'addr_key': ['UT CAMPUS'],
            'exclude_key': ['HARDIN', 'VALLEY']
        },
        '8': {
            'name_key': ['LENOIR', '16BPdwSY4rTxz1s5j'],
            'addr_key': ['LENOIR']
        },
        '9': {
            'name_key': ['PAPERMILL', '169lRsSY4qSev1u1U', 'LANDMARK', '*MASTER*'],
            'addr_key': ['BROOKVALE', 'PAPERMILL']
        },
        '10': {
            'name_key': ['BISTRO', 'BYTBIS'],
            'addr_key': ['BROOKVIEW']
        },
        '11': {
            'name_key': ['CLEVELAND', '16BPdwSY4rdjD1sEP'],
            'addr_key': ['CLEVELAND']
        },
        '12': {
            'name_key': ['BLUETICK', 'BLUMAR', "BARLEY'S MARYVILLE", 'BARLEY'],
            'addr_key': ['BROADWAY', 'BLUE TICK'],
            'exclude_key': ['AzqNMmSY4qGKj1rhz']
        },
        '13': {
            'name_key': ['RIDGE', '16CVqvSY4rpAd1xwu', '- OR'],
            'addr_key': ['RIDGE', '- OR']
        },
        '14': {
            'name_key': ['STRAW', '6olk9SY4mVGw1oZS', 'AUBSTR', 'STRAWPLAINS'],
            'addr_key': ['HUCKLEBERRY', 'STRAWPLAINS']
        },
        '15': {
            'name_key': ['SOCIAL', 'FIEKNO', 'FIELD HOUSE'],
            'addr_key': ['UNIVERSITY', 'FIELD HOUSE']
        },
        '16': {
            'name_key': ['GREEN', 'AzqNMmSY4ryrA1tGC', 'AUBGRE', 'GREENEVILLE'],
            'addr_key': ['GREENEVILLE', 'GREENVILLE']
        },
        '17': {
            'name_key': ['BRISTOL', '16CHy7SY4s9162seP', 'AUBBRI'],
            'addr_key': ['PINNACLE', 'BRISTOL']
        },
        '18': {
            'name_key': ['MORRISTOWN', '169lRsSY4sLmL1vml', 'AUBMOR', 'MORRIST'],
            'addr_key': ['EVAN GREEN', 'MORRISTOWN']
        },
        '20': {
            'name_key': ['CATERING', '919', 'BYTCAT'],
            'addr_key': ['HOMBERG', 'CENTRAL AVE']
        },
        '21': {
            'name_key': ['JOHNSON', 'JC', '16COOrSY4sXNu1qdT', 'AUBJOH'],
            'addr_key': ['HAMILTON PLACE', 'HAMILTON', 'JOHNSON']
        },
        '22': {
            'name_key': ['HARDIN', 'VALLEY'],
            'addr_key': ['HARDIN']
        },
        '23': {
            'name_key': ['SEVIERVILLE', '169lRsSY4sihy1w7h'],
            'addr_key': ['DOLLY PARTON', 'SEVIERVILLE']
        }
    }

    loc_id = '99'
    
    if not invoice_uri:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            invoice_uri = req_body.get('uri')

    if not key:
        key = req_body.get('key')
     
    if invoice_uri:
        form_recognizer_client = FormRecognizerClient(endpoint, AzureKeyCredential(key))
        poller = form_recognizer_client.begin_recognize_invoices_from_url(invoice_uri)
        #Swap the 2 lines above with the two lines below to switch to newer version of FormRecognizer
        #document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        #poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-invoice", invoice_uri)
        
        invoices = poller.result()
        json_dict={}
        items = []
        
        for invoice in invoices:
        #Swap the previous line with the next line to switch to newer version of FormRecognizer
        #for invoice in invoices.documents:
            vendor_name = invoice.fields.get("VendorName")    
            vendor_address = invoice.fields.get("VendorAddress")
            vendor_address_recipient = invoice.fields.get("VendorAddressRecipient")
            customer_name = invoice.fields.get("CustomerName")
            customer_id = invoice.fields.get("CustomerId")
            customer_address = invoice.fields.get("CustomerAddress")
            customer_address_recipient = invoice.fields.get("CustomerAddressRecipient")
            invoice_id = invoice.fields.get("InvoiceId")
            invoice_date = invoice.fields.get("InvoiceDate")
            invoice_total = invoice.fields.get("InvoiceTotal")
            due_date = invoice.fields.get("DueDate")
            purchase_order = invoice.fields.get("PurchaseOrder")
            billing_address = invoice.fields.get("BillingAddress")
            billing_address_recipient = invoice.fields.get("BillingAddressRecipient")
            shipping_address = invoice.fields.get("ShippingAddress")
            shipping_address_recipient = invoice.fields.get("ShippingAddressRecipient")
            subtotal = invoice.fields.get("SubTotal")
            total_tax = invoice.fields.get("TotalTax")
            previous_unpaid_balance = invoice.fields.get("PreviousUnpaidBalance")
            amount_due = invoice.fields.get("AmountDue")
            service_start_date = invoice.fields.get("ServiceStartDate")
            service_end_date = invoice.fields.get("ServiceEndDate")
            service_address = invoice.fields.get("ServiceAddress")
            service_address_recipient = invoice.fields.get("ServiceAddressRecipient")
            remittance_address = invoice.fields.get("RemittanceAddress")
            remittance_address_recipient = invoice.fields.get("RemittanceAddressRecipient")
            
            if remittance_address_recipient:
                json_dict['vendor_name'] = str(remittance_address_recipient.value.replace("'", "''"))
            elif vendor_name:
                json_dict['vendor_name'] = str(vendor_name.value.replace("'", "''"))
            elif vendor_address:
                json_dict['vendor_name'] = str(vendor_address.value.replace("'", "''"))
            elif vendor_address_recipient:
                json_dict['vendor_name'] = str(vendor_address_recipient.value.replace("'", "''"))
            elif remittance_address:
                json_dict['vendor_name'] = str(remittance_address.value.replace("'", "''"))
            else:
                json_dict['vendor_name'] = ''

            json_dict['loc_name'] = ''
            json_dict['summarized'] = False

            for vendor in vendor_dict:
                if json_dict['vendor_name'].upper().find(vendor.upper()) >= 0:
                    json_dict['vendor_name'] = vendor_dict[vendor]['sage_id']
                    json_dict['summarized'] = vendor_dict[vendor]['inv_summarized']

                    if vendor_dict[vendor]['cust_name_type'] == 'cust_name':
                        if customer_name:
                            json_dict['loc_name'] = str(customer_name.value.replace("'", "''"))
                    elif vendor_dict[vendor]['cust_name_type'] == 'serv_name':
                        if service_address_recipient:
                            json_dict['loc_name'] = str(service_address_recipient.value.replace("'", "''"))
                    elif vendor_dict[vendor]['cust_name_type'] == 'bill_name':
                        if billing_address:     
                            json_dict['loc_name'] = str(billing_address_recipient.value.replace("'", "''"))
                    elif vendor_dict[vendor]['cust_name_type'] == 'ship_name':
                        if shipping_address_recipient:
                            json_dict['loc_name'] = str(shipping_address_recipient.value.replace("'", "''"))
            
            if not json_dict['loc_name']:
                if customer_name:
                    json_dict['loc_name'] = str(customer_name.value.replace("'", "''"))
                elif shipping_address_recipient:
                    json_dict['loc_name'] = str(shipping_address_recipient.value.replace("'", "''"))
                elif service_address_recipient:
                    json_dict['loc_name'] = str(service_address_recipient.value.replace("'", "''"))
                elif customer_id:
                    json_dict['loc_name'] = str(customer_id.value.replace("'", "''"))
                elif customer_address_recipient:
                    json_dict['loc_name'] = str(customer_address_recipient.value.replace("'", "''"))
                elif billing_address_recipient:
                    json_dict['loc_name'] = str(billing_address_recipient.value.replace("'", "''"))
                else:
                    json_dict['loc_name'] = ''

            if customer_address:
                json_dict['loc_addr'] = str(customer_address.value.replace("'", "''"))
            elif shipping_address:
                json_dict['loc_addr'] = str(shipping_address.value.replace("'", "''"))
            elif billing_address:
                json_dict['loc_addr'] = str(billing_address.value.replace("'", "''"))
            elif service_address:
                json_dict['loc_addr'] = str(service_address.value.replace("'", "''"))
            else:
                json_dict['loc_addr'] = ''

            if invoice_id:
                json_dict['inv_number'] = str(invoice_id.value.replace("'", "''"))
            elif purchase_order:
                json_dict['inv_number'] = str(purchase_order.value.replace("'", "''"))
            else:
                json_dict['inv_number'] = ''

            #Make sure leading character of invoice number is alphanumeric
            if json_dict['inv_number']:
                while not json_dict['inv_number'][0].isalnum():
                    json_dict['inv_number'] = json_dict['inv_number'][1:len(json_dict['inv_number'])]

            key_found = False
            exclude_key = False
                
            for loc in location_dict:
                for key in location_dict[loc]['name_key']:
                    if json_dict['loc_name'].upper().find(key.upper()) >= 0:
                        key_found = True
                    if not key_found:
                        if json_dict['loc_addr'].upper().find(key.upper()) >= 0:
                            key_found = True

                    if 'exclude_key' in location_dict[loc]:
                        for excl in location_dict[loc]['exclude_key']:
                            if json_dict['loc_name'].upper().find(excl.upper()) >= 0:
                                exclude_key = True
                            if not exclude_key:
                                if json_dict['loc_addr'].upper().find(excl.upper()) >= 0:
                                    exclude_key = True
                                
                    if key_found and not exclude_key:
                        loc_id = loc
                        
                    key_found = exclude_key = False

                if loc_id == '99':
                    for key in location_dict[loc]['addr_key']:
                        if json_dict['loc_addr'].upper().find(key.upper()) >= 0:
                            loc_id = loc

            if vendor_dict[sage_vendors[json_dict['vendor_name']]]['expect_loc_id']:
                json_dict['inv_number'] = loc_id + '-' + json_dict['inv_number']

            if invoice_date:
                json_dict['inv_date'] = str(invoice_date.value)
            elif due_date:
                json_dict['inv_date'] = str(due_date.value)
            elif service_start_date:
                json_dict['inv_date'] = str(service_start_date.value)
            elif service_end_date:
                json_dict['inv_date'] = str(service_end_date.value)
            else:
                json_dict['inv_date'] = ''

            if 'inv_total_field' in vendor_dict[sage_vendors[json_dict['vendor_name']]]:
                if vendor_dict[sage_vendors[json_dict['vendor_name']]]['inv_total_field'] == 'invoice_total':
                    if invoice_total:
                        json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(invoice_total.value).replace('(', '-'))[0]
                elif vendor_dict[sage_vendors[json_dict['vendor_name']]]['inv_total_field'] == 'amount_due':
                    if amount_due:
                        json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(amount_due.value).replace('(', '-'))[0]
                elif vendor_dict[sage_vendors[json_dict['vendor_name']]]['inv_total_field'] == 'subtotal':
                    if subtotal:
                        json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(subtotal.value).replace('(', '-'))[0]
                elif vendor_dict[sage_vendors[json_dict['vendor_name']]]['inv_total_field'] == 'previous_unpaid_balance':
                    if previous_unpaid_balance:
                        json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(previous_unpaid_balance.value).replace('(', '-'))[0]
                    else:
                        if json_dict['vendor_name'] == 'VIENNA':
                            # Known Issue acquiring Vienna Coffee Invoice Totals
                            # The actual invoice total is not available as a field in the invoice results
                            # Work around is to use a prebuilt model specifically for this vendor

                            vienna_model_id = 'e492f78b-0731-4c8d-85ff-8c49c2efd080'

                            vienna_poller = form_recognizer_client.begin_recognize_custom_forms_from_url(
                                model_id=vienna_model_id,
                                form_url=invoice_uri
                            ) 
                            vienna_invoice = poller.result()
                            
                            for v in vienna_invoice:
                                vienna_total = v.fields.get("InvoiceTotal")
                                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(vienna_total.value).replace('(', '-'))[0]

            if not 'inv_total' in json_dict:
                if invoice_total:
                    json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(invoice_total.value).replace('(', '-'))[0]
                elif amount_due:
                    json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(amount_due.value).replace('(', '-'))[0]
                elif subtotal:
                    json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(subtotal.value).replace('(', '-'))[0]
                elif previous_unpaid_balance:
                    json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(previous_unpaid_balance.value).replace('(', '-'))[0]
                else:
                    json_dict['inv_total'] = ''
            
            for idx, item in enumerate(invoice.fields.get("Items").value):
                line_item = {}
                description = item.value.get("Description")
                try:
                    line_item['description'] = str(description.value.replace("'", "''"))
                except:
                    line_item['description'] = ''

                quantity = item.value.get("Quantity")
                try:
                    line_item['quantity'] = re.findall(r"[-+]?\d*\.\d+|\d+", str(quantity.value))[0]
                except:
                    line_item['quantity'] = 'NULL'

                unit = item.value.get("Unit")
                try:
                    line_item['unit'] = str(unit.value.replace("'", "''"))
                except:
                    line_item['unit'] = ''
                
                unit_price = item.value.get("UnitPrice")
                try:
                    line_item['unit_price'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(unit_price.value).replace('(', '-'))[0]
                except:
                    line_item['unit_price'] = 'NULL'
                    
                product_code = item.value.get("ProductCode")
                try:
                    if vendor_dict[sage_vendors[json_dict['vendor_name']]]['inv_summarized']:
                        for loc in location_dict:
                            for key in location_dict[loc]['name_key']:
                                if line_item['description'].upper().find(key.upper()) >= 0:
                                    loc_id  = loc
                                
                        line_item['product_code'] = loc_id + '-' + str(product_code.value.replace("'", "''"))
                    else:
                        line_item['product_code'] = str(product_code.value.replace("'", "''"))
                except:
                    line_item['product_code'] = ''
                    
                date = item.value.get("Date")
                try:
                    line_item['date'] = str(date.value)
                except:
                    line_item['date'] = ''

                tax = item.value.get("Tax")
                try:
                    line_item['tax'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(tax.value).replace('(', '-'))[0]
                except:
                    line_item['tax'] = 'NULL'
                    
                amount = item.value.get("Amount")
                try:
                    line_item['amount'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(amount.value).replace('(', '-'))[0]
                except:
                    line_item['amount'] = 'NULL'

                items.append(line_item)

            if items:
                json_dict['line_items'] = items

        '''
        Beta Version Having Issues - Save Code for possible future use
        #Form Recognizer v3.2.0b3 doesn't pick up invoices dates as well as previous versions.
        #If no date is found, the following code looks for any words in the document with two back slashes
        #Orders any matches and outputs the oldest date
        if not json_dict['inv_date']:
            dates = []
            for w in invoices.pages[0].words:
                if w.content.count('/') == 2:
                    sl_one = w.content.find('/')
                    sl_two = w.content.find('/', sl_one + 1)

                    try:    #See if value is really a date
                        m = int(w.content[:sl_one])
                        d = int(w.content[sl_one+1:sl_two])
                        y = int(w.content[sl_two+1:])

                        date_conv = datetime(y, m, d)

                        dates.append(w.content)
                    except:
                        no_val = ''
        
            if len(dates) > 0:
                dates.sort(reverse=False)
                json_dict['inv_date'] = dates[0]    #Select the oldest date
        '''
        
        #return func.HttpResponse("Test 3", status_code=210)
        return func.HttpResponse(
            json.dumps(
                json_dict
            ),
            mimetype='application/json'
        )
        
    else:
        return func.HttpResponse(
             "Not enough information to process invoice. Check that both Vendor and Invoice URI were passed.",
             status_code=200
        )
