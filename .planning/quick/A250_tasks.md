I have updated the input fields for my form in app.py. This form is saved here: C:\Users\abindal\Documents\00_Python\MarketingFolderCreation\templates\A250.docx

Now, in the form we have to make the following edits

1) {{requested_by}} = {{client_name}}, {{client_license}}, {{client_title}}\n{{client}}: Based on the length of these entries, I may be forced to add another \n before Title.
2) {{invoice_to}} = Same as "Requested By"\n{{client}} by default or something custom that the user writes
3) {{client_signed}} = {{client_name}}, {{client_title}}. If the length of the content is large, I want a \n before client title.
4) I should be allowed to enter the entries in a rich text format, including but not limited to enters, tabs, bolds, italics, underline
5) I should be able to select from a dropdown for Principal, project manager, fee type.
