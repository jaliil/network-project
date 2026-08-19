from django import forms
from .models import Device, Province

class DeviceForm(forms.ModelForm):
    province = forms.ModelChoiceField(
        queryset=Province.objects.all(),
        required=False,
        empty_label="- Select Province -",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_province'})
    )

    class Meta:
        model = Device
        fields = [
            'province', 
            'bts', 
            'device_type', 
            'name', 
            'ip_address', 
            'mac_address', 
            'has_adapter', 
            'has_poe', 
            'device_model',
            'ssid', 
            'frequency'
        ]
        
        widgets = {
            'bts': forms.Select(attrs={'class': 'form-select', 'id': 'id_bts'}),
            'device_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_device_type'}),
            'device_model': forms.Select(attrs={'class': 'form-select', 'id': 'id_device_model'}),
            
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Device Name'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.x.x'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XX:XX:XX:XX:XX:XX'}),
            
            'has_adapter': forms.CheckboxInput(attrs={'class': 'form-check-input mt-0', 'id': 'id_has_adapter', 'style': 'cursor: pointer; width: 1.5em; height: 1.5em; border-radius: 4px; border: 2px solid #cbd5e1;'}),
            'has_poe': forms.CheckboxInput(attrs={'class': 'form-check-input mt-0', 'id': 'id_has_poe', 'style': 'cursor: pointer; width: 1.5em; height: 1.5em; border-radius: 4px; border: 2px solid #cbd5e1;'}),
            
            'ssid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SSID'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Frequency'}),
        }
        
    def __init__(self, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)
        self.fields['bts'].empty_label = "- Select Tower -"
        self.fields['device_type'].choices = [('', '- Select -')] + list(self.fields['device_type'].choices)[1:]
        self.fields['device_model'].choices = [('', '- Select -')] + list(self.fields['device_model'].choices)[1:]