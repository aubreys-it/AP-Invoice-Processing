from dataclasses import fields
import json, re
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import FormRecognizerClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from datetime import datetime
from . import __locations__, __vendors__
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    #logging.info('Python HTTP trigger function processed a request.')

    invoice_uri = req.params.get('uri')
    key = req.params.get('key')
    endpoint = "https://ap-formrecognizer.cognitiveservices.azure.com/"
    
    vendor_dict = __vendors__.vendor_dict
    
    sage_vendors = {}
    for v in vendor_dict.keys():
        sage_vendors[vendor_dict[v]['sage_id']] = v

    location_dict = __locations__.location_dict

    # Location 20, name key 919 shows up in other location addresses regularly
    # to fix the issue, we add all the other locations name and address keys
    # to 20's exclude key
    for loc in location_dict:
        if loc != '20':
            for k in location_dict[loc]['name_key']:
                location_dict['20']['exclude_key'].append(k)
            for k in location_dict[loc]['addr_key']:
                location_dict['20']['exclude_key'].append(k)

    # Default location number
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
        #form_recognizer_client = FormRecognizerClient(endpoint, AzureKeyCredential(key))
        #poller = form_recognizer_client.begin_recognize_invoices_from_url(invoice_uri)
        #Swap the 2 lines above with the two lines below to switch to newer version of FormRecognizer
        document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-invoice", invoice_uri)
        
        invoices = poller.result()
        json_dict={}
        items = []
        word_list = []

        #for invoice in invoices:
        #Swap the previous line with the next line to switch to newer version of FormRecognizer
        for invoice in invoices.documents:
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
            
            vendor_info = []

            if vendor_address_recipient:
                vendor_info.append(vendor_address_recipient.to_dict()['content'])
            if remittance_address_recipient:
                vendor_info.append(remittance_address_recipient.to_dict()['content'])
            if vendor_name:
                vendor_info.append(vendor_name.to_dict()['content'])
            if vendor_address:
                vendor_info.append(vendor_address.to_dict()['content'])
            if remittance_address:
                vendor_info.append(remittance_address.to_dict()['content'])

            logging.info(vendor_info)

            for info in vendor_info:
                for vendor in vendor_dict:
                    vendor_match = []
                    vendor_match.append(vendor)
                    if 'address' in vendor_dict[vendor].keys():
                        vendor_match.append(vendor_dict[vendor]['address'])

                    for v in vendor_match:
                        if info.upper().find(v.upper()) >= 0 or v.upper().find(info.upper()) >= 0:
                            json_dict['vendor_name'] = vendor_dict[vendor]['sage_id']
                            json_dict['summarized'] = vendor_dict[vendor]['inv_summarized']

                            if vendor_dict[vendor]['cust_name_type'] == 'cust_name':
                                if customer_name:
                                    json_dict['loc_name'] = customer_name.value
                            elif vendor_dict[vendor]['cust_name_type'] == 'serv_name':
                                if service_address_recipient:
                                    json_dict['loc_name'] = service_address_recipient.value
                            elif vendor_dict[vendor]['cust_name_type'] == 'bill_name':
                                if billing_address:     
                                    json_dict['loc_name'] = billing_address_recipient.value
                            elif vendor_dict[vendor]['cust_name_type'] == 'ship_name':
                                if shipping_address_recipient:
                                    json_dict['loc_name'] = shipping_address_recipient.value
                            elif vendor_dict[vendor]['cust_name_type'] == 'vend_name':
                                if vendor_address_recipient:
                                    json_dict['loc_name'] = vendor_address_recipient.value

                            if 'loc_name' in json_dict:
                                logging.info(json_dict['loc_name'])
                                json_dict['loc_name'] = str(json_dict['loc_name']).replace("'", "''")

                if 'vendor_name' in json_dict:
                    break

            if json_dict['vendor_name'] == 'PREPWIZ':
                # Known Issue with PrepWizard Invoices not finding store location information
                # This work around uses a custom model to find the missing info

                pw_model_id = vendor_dict['PREPWIZARD']['custom_model_id']

                pw_poller = document_analysis_client.begin_analyze_document_from_url(
                    model_id=pw_model_id,
                    document_url=invoice_uri
                    )

                #pw_poller = form_recognizer_client.begin_recognize_custom_forms_from_url(
                #    model_id=pw_model_id,
                #    form_url=invoice_uri
                #    ) 
                pw_invoice = pw_poller.result()
                
                for v in pw_invoice.documents:
                    pw_location = v.fields.get("LocationName")
                    json_dict['loc_name'] = str(pw_location.value.replace("'", "''"))

            elif not 'loc_name' in json_dict:
                if customer_name:
                    json_dict['loc_name'] = customer_name.value
                elif shipping_address_recipient:
                    json_dict['loc_name'] = shipping_address_recipient.value
                elif service_address_recipient:
                    json_dict['loc_name'] = service_address_recipient.value
                elif customer_id:
                    json_dict['loc_name'] = customer_id.value
                elif customer_address_recipient:
                    json_dict['loc_name'] = customer_address_recipient.value
                elif billing_address_recipient:
                    json_dict['loc_name'] = billing_address_recipient.value
                else:
                    json_dict['loc_name'] = ''
                json_dict['loc_name'] = str(json_dict['loc_name']).replace("'", "''")

            if customer_address:
                json_dict['loc_addr'] = customer_address.to_dict()['content']
            elif shipping_address:
                json_dict['loc_addr'] = shipping_address.to_dict()['content']
            elif billing_address:
                json_dict['loc_addr'] = billing_address.to_dict()['content']
            elif service_address:
                json_dict['loc_addr'] = service_address.to_dict()['content']
            else:
                json_dict['loc_addr'] = ''
            json_dict['loc_addr'] = str(json_dict['loc_addr']).replace("'", "''")

            logging.info(json_dict['loc_addr'])

            if invoice_id:
                json_dict['inv_number'] = str(invoice_id.value.replace("'", "''"))
            elif purchase_order:
                json_dict['inv_number'] = str(purchase_order.value.replace("'", "''"))
            else:
                json_dict['inv_number'] = ''

            # If inv_number contains a space, only grab what's left of the space
            if json_dict['inv_number'].find(' ') >= 0:
                json_dict['inv_number'] = json_dict['inv_number'][0:json_dict['inv_number'].find(' ')]

            #Make sure leading character of invoice number is alphanumeric
            if json_dict['inv_number']:
                while not json_dict['inv_number'][0].isalnum():
                    json_dict['inv_number'] = json_dict['inv_number'][1:len(json_dict['inv_number'])]

            key_found = False
            exclude_key = False

            #_Get_Location_ID_________________________________________________________________________________________________________________
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

                # If location not found in the customer name field, then look through addresses for keywords
                if loc_id == '99':
                    for key in location_dict[loc]['addr_key']:
                        if json_dict['loc_addr'].upper().find(key.upper()) >= 0:
                            loc_id = loc
            #_________________________________________________________________________________________________________________________________

            if vendor_dict[sage_vendors[json_dict['vendor_name']]]['expect_loc_id'] and loc_id != '0':
                json_dict['inv_number'] = loc_id + '-' + json_dict['inv_number']

            if invoice_date and invoice_date.value != None:
                json_dict['inv_date'] = str(invoice_date.value)
            elif due_date:
                json_dict['inv_date'] = str(due_date.value)
            elif service_start_date:
                json_dict['inv_date'] = str(service_start_date.value)
            elif service_end_date:
                json_dict['inv_date'] = str(service_end_date.value)
            else:
                json_dict['inv_date'] = ''

            if amount_due:
                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(amount_due.value).replace('(', '-'))[0]
            elif invoice_total.value:
                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(invoice_total.value).replace('(', '-'))[0]
            elif invoice_total.value_data.text:
                invoiceValue = invoice_total.value_data.text

                if not invoiceValue[-3].isnumeric():
                    invoiceValue = invoiceValue[0:-3] + '.' + invoiceValue[-2:]
                else:
                    invoiceValue += '.'
                
                dotPosition = len(invoiceValue) - invoiceValue.rindex('.')
                invoiceValue = invoiceValue.replace('.', '')
                json_dict['inv_total'] = invoiceValue[0:dotPosition] + '.' + invoiceValue[dotPosition:]
            elif subtotal:
                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(subtotal.value).replace('(', '-'))[0]
            elif previous_unpaid_balance:
                json_dict['inv_total'] = re.findall(r"[-+]?\d*\.\d+|\d+\-", str(previous_unpaid_balance.value).replace('(', '-'))[0]
            else:
                json_dict['inv_total'] = ''
            
            try:
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
            except:
                items=[]

            if items:
                json_dict['line_items'] = items

        # If location still not found, search through all invoice words for keywords
        if loc_id == '99':
            for key in json_dict:
                word_list.append(json_dict[key])
            if json_dict['line_items']:
                for line in json_dict['line_items']:
                    for key in line:
                        word_list.append(line[key])

            for loc in location_dict:
                    for key in location_dict[loc]['name_key']:
                        key_found = key.upper() in word_list
                        if 'exclude_key' in location_dict[loc]:
                            for excl in location_dict[loc]['exclude_key']:
                                if not exclude_key:
                                    exclude_key = excl.upper() in word_list
                        if key_found and not exclude_key:
                            loc_id = loc
                            break
                        key_found = exclude_key = False
                    if loc_id != '99':
                        break

        
        #Beta Version Having Issues - Save Code for possible future use
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

        #Remove newline characters from json_dict values
        for key in json_dict:
            if isinstance(json_dict[key], str):
                if json_dict[key].find('\n') >= 0:            
                    json_dict[key] = json_dict[key] = json_dict[key][:json_dict[key].find('\n')]
        
        
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