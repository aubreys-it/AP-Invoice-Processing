import json, re
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import FormRecognizerClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    #logging.info('Python HTTP trigger function processed a request.')

    invoice_uri = req.params.get('uri')

    endpoint = "https://ap-formrecognizer.cognitiveservices.azure.com/"
    
    #keys based on unique keywords in vendor name
    vendor_dict = {
        'AQUA CLEAR': {
            'cust_name_type': 'serv_name',
            'sage_id': 'AQUA CL',
            'inv_summarized': False
        },
        'CARTRIDGE': {
            'cust_name_type': 'ship_name',
            'sage_id': 'CARTRID',
            'inv_summarized': False
        },
        'COZZINI': {
            'cust_name_type': 'ship_name',
            'sage_id': 'COZZINI',
            'inv_summarized': False
        },
        'HOBART': {
            'cust_name_type': 'serv_name',
            'sage_id': 'HOB SER',
            'inv_summarized': False
        },
        'J & F MECHANICAL': {
            'cust_name_type': 'bill_name',
            'sage_id': 'J&F MEC',
            'inv_summarized': False
        },
        'NIEDLOV': {
            'cust_name_type': 'ship_name',
            'sage_id': 'NIEDLOV',
            'inv_summarized': False
        },
        'PREPWIZARD': {
            'cust_name_type': 'ship_name',
            'sage_id': 'PREPWIZARD',
            'inv_summarized': False
        },
        'PRODUCE': {
            'cust_name_type': 'ship_name',
            'sage_id': 'VALL',
            'inv_summarized': False
        },
        'QUALITY BAKER': {
            'cust_name_type': 'cust_name',
            'sage_id': 'QuAL BA',
            'inv_summarized': False
        },
        'TRITEX': {
            'cust_name_type': 'cust_name',
            'sage_id': 'TRITEX',
            'inv_summarized': False
        },
        'VIENNA': {
            'cust_name_type': 'ship_name',
            'sage_id': 'VIENNA',
            'inv_summarized': False
        },
        'WASSERSTROM': {
            'cust_name_type': 'ship_name',
            'sage_id': 'WASSERS',
            'inv_summarized': False
        },
        'WORLD': {
            'cust_name_type': 'in_table',
            'sage_id': 'WORLDSP',
            'inv_summarized': True
        }
    }

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
            'addr_key': ['- MARYVILLE']
        },
        '6': {
            'name_key': ['HIXSON', '169lRsSY4rjvz1ulr', 'CHATTANOOGA'],
            'addr_key': ['CHATTANOOGA', 'HIXSON']
        },
        '7': {
            'name_key': ['UT CAMPUS'],
            'addr_key': ['UT CAMPUS']
        },
        '8': {
            'name_key': ['LENOIR', '16BPdwSY4rTxz1s5j'],
            'addr_key': ['LENOIR']
        },
        '9': {
            'name_key': ['PAPERMILL', '169lRsSY4qSev1u1U', 'LANDMARK'],
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
            'name_key': ['BLUETICK', 'BLUMAR'],
            'addr_key': ['BROADWAY', 'BLUE TICK']
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
            'addr_key': ['HOMBERG', '919', 'CENTRAL AVE']
        },
        '21': {
            'name_key': ['JOHNSON', 'JC', '16COOrSY4sXNu1qdT', 'AUBJOH'],
            'addr_key': ['HAMILTON PLACE', 'HAMILTON', 'JOHNSON']
        },
        '22': {
            'name_key': ['HARDIN'],
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
            invoice__uri = req_body.get('uri')
            #key = req_body.get('key')

    key_dict = { 'key': 'key' }

    if invoice_uri:
        form_recognizer_client = FormRecognizerClient(endpoint, AzureKeyCredential(key))
        poller = form_recognizer_client.begin_recognize_invoices_from_url(invoice_uri)

        invoices = poller.result()
        json_dict={}
        items = []
        
        for invoice in invoices:
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

            if vendor_name:
                json_dict['vendor_name'] = str(vendor_name.value.replace("'", "''"))
            elif vendor_address:
                json_dict['vendor_name'] = str(vendor_address.value.replace("'", "''"))
            elif vendor_address_recipient:
                json_dict['vendor_name'] = str(vendor_address_recipient.value.replace("'", "''"))
            else:
                json_dict['vendor_name'] = ''

            json_dict['loc_name'] = ''
            json_dict['summarized'] = False

            for vendor in vendor_dict:
                if json_dict['vendor_name'].upper().find(vendor.upper()) >= 0:
                    json_dict['vendor_name'] = vendor_dict[vendor]['sage_id']
                    json_dict['summarized'] = vendor_dict[vendor]['inv_summarized']

                    if vendor_dict[vendor]['cust_name_type'] == 'cust_name':
                        json_dict['loc_name'] = str(customer_name.value.replace("'", "''"))
                    elif vendor_dict[vendor]['cust_name_type'] == 'serv_name':
                        json_dict['loc_name'] = str(service_address_recipient.value.replace("'", "''"))
                    elif vendor_dict['loc_name']['cust_name_type'] == 'bill_name':
                        json_dict['loc_name'] = str(billing_address_recipient.value.replace("'", "''"))
                    elif vendor_dict[vendor]['cust_name_type'] == 'ship_name':
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
                elif remittance_address_recipient:
                    json_dict['loc_name'] = str(remittance_address_recipient.value.replace("'", "''"))
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
            elif remittance_address:
                json_dict['loc_addr'] = str(remittance_address.value.replace("'", "''"))
            else:
                json_dict['loc_addr'] = ''

            if invoice_id:
                json_dict['inv_number'] = str(invoice_id.value.replace("'", "''"))
            elif purchase_order:
                json_dict['inv_number'] = str(purchase_order.value.replace("'", "''"))
            else:
                json_dict['inv_number'] = ''

            for loc in location_dict:
                for key in location_dict[loc]['name_key']:
                    if json_dict['loc_name'].upper().find(key.upper()) >= 0:
                        loc_id = loc

                if loc_id == '99':
                    for key in location_dict[loc]['addr_key']:
                        if json_dict['loc_addr'].upper().find(key.upper()) >= 0:
                            loc_id = loc

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

            if invoice_total:
                #json_dict['inv_total'] = invoice_total
                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(invoice_total.value_data.text.replace('(', '-')))[0]
            elif amount_due:
                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(amount_due.value_data.text.replace('(', '-')))[0]
            elif subtotal:
                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(subtotal.value_data.text.replace('(', '-')))[0]
            else:
                json_dict['inv_total'] = ''
            
            for idx, item in enumerate(invoice.fields.get("Items").value):
                line_item = {}
                description = item.value.get("Description")
                if description:
                    line_item['description'] = str(description.value.replace("'", "''"))
                else:
                    line_item['description'] = ''

                quantity = item.value.get("Quantity")
                if quantity:
                    line_item['quantity'] = re.findall(r"[-+]?\d*\.\d+|\d+", str(quantity.value))[0]
                else:
                    line_item['quantity'] = 'NULL'

                unit = item.value.get("Unit")
                if unit:
                    line_item['unit'] = str(unit.value.replace("'", "''"))
                else:
                    line_item['unit'] = ''
                
                unit_price = item.value.get("UnitPrice")
                if unit_price:
                    line_item['unit_price'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(unit_price.value_data.text.replace('(', '-')))[0]
                else:
                    line_item['unit_price'] = 'NULL'
                    
                product_code = item.value.get("ProductCode")
                if product_code:
                    line_item['product_code'] = str(product_code.value.replace("'", "''"))
                else:
                    line_item['product_code'] = ''
                    
                date = item.value.get("Date")
                if date:
                    line_item['date'] = str(date.value)
                else:
                    line_item['date'] = ''

                tax = item.value.get("Tax")
                if tax:
                    line_item['tax'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(tax.value_data.text.replace('(', '-')))[0]
                else:
                    line_item['tax'] = 'NULL'
                    
                amount = item.value.get("Amount")
                if amount:
                    line_item['amount'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(amount.value_data.text.replace('(', '-')))[0]
                else:
                    line_item['amount'] = 'NULL'

                items.append(line_item)

            if items:
                json_dict['line_items'] = items

            

        #return func.HttpResponse("Test 3", status_code=210)

        return func.HttpResponse(
            json.dumps(
                key_dict
            ),
            mimetype='application/json'
        )

    else:
        return func.HttpResponse(
             "Not enough information to process invoice. Check that both Vendor and Invoice URI were passed.",
             status_code=200
        )
    