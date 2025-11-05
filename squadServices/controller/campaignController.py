import csv
import io
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from squadServices.models.campaign import Campaign, CampaignContact

def is_valid_contact(contact):
    return contact.isdigit() and 7 <= len(contact) <= 15
class CampaignContactBulkCreateAPIView(APIView):
    def post(self,request):
        
        campaignId=request.data.get('campaignId')
        file=request.FILES.get("csvFile")
        contactsData = request.data.get('contacts', '').strip()
        campaign= Campaign.objects.get(id=campaignId)
        createdContacts=[]
        skippedDuplicates=[]
        invalidContacts = []
        duplicateInInput = []
        existingContacts = set(CampaignContact.objects.filter(campaign=campaign).values_list('contactNumber', flat=True))
        seenInputs = set()

        if file:
            try:
                decodedFile = file.read().decode('utf-8')
            except UnicodeDecodeError:
                file.seek(0)
                decodedFile = file.read().decode('latin1')

            ioString=io.StringIO(decodedFile)
            reader = csv.DictReader(ioString)

            for row in reader:
                row_lower = {k.lower(): v for k, v in row.items()}

                for contact in row:
                    contact = row_lower.get('contact', '').strip()
                    if contact and contact in seenInputs:
                        duplicateInInput.append(contact)
                    else:
                        seenInputs.add(contact)
                        if is_valid_contact(contact) and contact not in existingContacts:
                                createdContacts.append(CampaignContact(campaign=campaign, contactNumber=contact))
                                

                        elif contact in existingContacts:
                            skippedDuplicates.append(contact)
                        else:
                            invalidContacts.append(contact)
                 
        else:
            contactsData=contactsData
            if not contactsData:
                return Response({"error": "Field is required and cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

            if contactsData:
                contacts=[c.strip() for c in contactsData.split(",") if c.strip()]
                
                for contact in contacts:
                    if contact in seenInputs:
                        duplicateInInput.append(contact)
                    else:
                        seenInputs.add(contact)           
                        if is_valid_contact(contact) and contact not in existingContacts:
                            createdContacts.append(CampaignContact(campaign=campaign, contactNumber=contact))
                            

                        elif contact in existingContacts:
                            skippedDuplicates.append(contact)
                        else:
                            invalidContacts.append(contact)

        if createdContacts:
            CampaignContact.objects.bulk_create(createdContacts)
        createdContactNumbers = [c.contactNumber for c in createdContacts]

        return Response({
            "created": createdContactNumbers,
            "skippedDuplicates": skippedDuplicates,
            "invalidContacts": invalidContacts,
            "duplicateInInput" : duplicateInInput
        }, status=status.HTTP_201_CREATED)

                        
