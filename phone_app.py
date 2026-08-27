from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.animation import Animation
import sqlite3
import os
import re

Window.size = (400, 700)
Window.clearcolor = get_color_from_hex('#F5F5F7')

# ============ UTILITY FUNCTIONS ============
def parse_resistance(value_str):
    if not value_str:
        return None
    value_str = value_str.lower().replace(' ', '').replace('ω', '').replace('ohm', '')
    match = re.match(r'([\d.]+)\s*([km]?)', value_str)
    if not match:
        return None
    try:
        value = float(match.group(1))
        multiplier = match.group(2)
        if multiplier == 'k':
            value *= 1000
        elif multiplier == 'm':
            value *= 1000000
        return value
    except:
        return None

def parse_capacitance(value_str):
    if not value_str:
        return None
    value_str = value_str.lower().replace(' ', '')
    match = re.match(r'([\d.]+)\s*(pf|nf|uf|mf|f)?', value_str)
    if not match:
        return None
    try:
        value = float(match.group(1))
        unit = match.group(2) or 'uf'
        multipliers = {'pf': 1e-12, 'nf': 1e-9, 'uf': 1e-6, 'mf': 1e-3, 'f': 1}
        return value * multipliers.get(unit, 1e-6)
    except:
        return None

def get_resistor_colors(resistance_ohms, tolerance=None):
    if not resistance_ohms or resistance_ohms <= 0:
        return None
    color_map = {0: 'black', 1: 'brown', 2: 'red', 3: 'orange', 4: 'yellow',
                 5: 'green', 6: 'blue', 7: 'violet', 8: 'gray', 9: 'white'}
    tolerance_colors = {'1%': 'brown', '2%': 'red', '5%': 'gold', '10%': 'silver', '20%': 'none'}
    
    if resistance_ohms >= 100:
        temp = resistance_ohms
        while temp >= 100:
            temp /= 10
        first_digit = int(temp)
        second_digit = int((temp - first_digit) * 10)
        multiplier = len(str(int(resistance_ohms))) - 2
    elif resistance_ohms >= 10:
        first_digit = int(resistance_ohms / 10)
        second_digit = int(resistance_ohms % 10)
        multiplier = 0
    else:
        first_digit = int(resistance_ohms)
        second_digit = int((resistance_ohms - first_digit) * 10)
        multiplier = -1
    
    multiplier_colors = {-3: 'pink', -2: 'silver', -1: 'gold', 0: 'black', 1: 'brown',
                         2: 'red', 3: 'orange', 4: 'yellow', 5: 'green', 6: 'blue',
                         7: 'violet', 8: 'gray', 9: 'white'}
    
    colors = [color_map.get(first_digit % 10, 'black'),
              color_map.get(second_digit % 10, 'black'),
              multiplier_colors.get(multiplier, 'black')]
    colors.append(tolerance_colors.get(tolerance, 'gold'))
    return colors

def get_capacitor_code(capacitance_farads):
    if not capacitance_farads or capacitance_farads <= 0:
        return None
    pf_value = capacitance_farads * 1e12
    if pf_value < 10:
        return f"{pf_value:.1f}pF"
    elif pf_value < 100:
        return f"{int(pf_value)}pF"
    elif pf_value < 1000:
        return f"{int(pf_value)}"
    else:
        pf_str = str(int(pf_value))
        first_digits = pf_str[:2]
        multiplier = len(pf_str) - 1
        return f"{first_digits}{multiplier}"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))

COLOR_HEX = {
    'black': '#000000', 'brown': '#8B4513', 'red': '#FF0000', 'orange': '#FF8C00',
    'yellow': '#FFD700', 'green': '#008000', 'blue': '#0000FF', 'violet': '#8B008B',
    'gray': '#808080', 'white': '#FFFFFF', 'gold': '#FFD700', 'silver': '#C0C0C0',
    'none': '#F5F5F7'
}

RESISTOR_VALUES = [
    '1Ω', '10Ω', '100Ω', '1kΩ', '10kΩ', '100kΩ', '1MΩ', '10MΩ',
    '2.2Ω', '22Ω', '220Ω', '2.2kΩ', '22kΩ', '220kΩ', '2.2MΩ',
    '4.7Ω', '47Ω', '470Ω', '4.7kΩ', '47kΩ', '470kΩ', '4.7MΩ'
]

CAPACITOR_VALUES = [
    '10pF', '100pF', '1nF', '10nF', '100nF', '1µF', '10µF', '100µF',
    '22pF', '220pF', '2.2nF', '22nF', '220nF', '2.2µF', '22µF', '220µF',
    '47pF', '470pF', '4.7nF', '47nF', '470nF', '4.7µF', '47µF', '470µF'
]

COMPONENT_TYPES = ['Resistor', 'Capacitor', 'LED', 'Diode', 'Transistor', 'IC', 'Inductor', 'Connector', 'Other']

TYPE_COLORS = {
    'resistor': '#4F46E5', 'capacitor': '#DC2626', 'led': '#10B981',
    'diode': '#F59E0B', 'transistor': '#8B5CF6', 'ic': '#EC4899',
    'inductor': '#06B6D4', 'connector': '#6B7280', 'other': '#6B7280'
}

# ============ DATABASE ============
class Database:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phone_inventory.db')
        self.create_tables()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                value TEXT,
                quantity INTEGER DEFAULT 0,
                location TEXT,
                notes TEXT,
                tolerance TEXT,
                wattage TEXT,
                capacitor_type TEXT,
                voltage_rating TEXT,
                needs_restock INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Planning',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                component_id INTEGER,
                quantity_needed INTEGER DEFAULT 1
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_component(self, comp_data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO components (type, name, value, quantity, location, notes, tolerance, wattage, capacitor_type, voltage_rating, needs_restock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comp_data.get('type', 'other'),
            comp_data.get('name', ''),
            comp_data.get('value', ''),
            comp_data.get('quantity', 0),
            comp_data.get('location', ''),
            comp_data.get('notes', ''),
            comp_data.get('tolerance', ''),
            comp_data.get('wattage', ''),
            comp_data.get('capacitor_type', ''),
            comp_data.get('voltage_rating', ''),
            comp_data.get('needs_restock', 0)
        ))
        conn.commit()
        conn.close()
    
    def update_component(self, comp_id, comp_data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE components SET type=?, name=?, value=?, quantity=?, location=?, notes=?
            WHERE id=?
        ''', (
            comp_data.get('type', 'other'),
            comp_data.get('name', ''),
            comp_data.get('value', ''),
            comp_data.get('quantity', 0),
            comp_data.get('location', ''),
            comp_data.get('notes', ''),
            comp_id
        ))
        conn.commit()
        conn.close()
    
    def get_component(self, comp_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM components WHERE id = ?', (comp_id,))
        component = cursor.fetchone()
        conn.close()
        return component
    
    def get_components(self, search='', type_filter=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = 'SELECT * FROM components WHERE 1=1'
        params = []
        if search:
            query += ' AND (name LIKE ? OR value LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])
        if type_filter:
            query += ' AND type = ?'
            params.append(type_filter)
        query += ' ORDER BY name'
        cursor.execute(query, params)
        components = cursor.fetchall()
        conn.close()
        return components
    
    def get_low_stock(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM components WHERE quantity < 5 AND needs_restock = 0 ORDER BY quantity')
        components = cursor.fetchall()
        conn.close()
        return components
    
    def get_shopping_list(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM components WHERE needs_restock = 1 ORDER BY name')
        components = cursor.fetchall()
        conn.close()
        return components
    
    def toggle_restock(self, comp_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT needs_restock FROM components WHERE id = ?', (comp_id,))
        current = cursor.fetchone()[0]
        new_val = 1 if current == 0 else 0
        cursor.execute('UPDATE components SET needs_restock = ? WHERE id = ?', (new_val, comp_id))
        conn.commit()
        conn.close()
    
    def delete_component(self, comp_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM project_components WHERE component_id = ?', (comp_id,))
        cursor.execute('DELETE FROM components WHERE id = ?', (comp_id,))
        conn.commit()
        conn.close()
    
    def add_project(self, name, description='', status='Planning'):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO projects (name, description, status) VALUES (?, ?, ?)',
                      (name, description, status))
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id
    
    def get_projects(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects ORDER BY created_at DESC')
        projects = cursor.fetchall()
        conn.close()
        return projects
    
    def delete_project(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM project_components WHERE project_id = ?', (project_id,))
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        conn.close()
    
    def add_component_to_project(self, project_id, component_id, quantity=1):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO project_components (project_id, component_id, quantity_needed) VALUES (?, ?, ?)',
                      (project_id, component_id, quantity))
        conn.commit()
        conn.close()
    
    def get_project_components(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pc.id, pc.quantity_needed, c.name, c.value
            FROM project_components pc
            JOIN components c ON pc.component_id = c.id
            WHERE pc.project_id = ?
        ''', (project_id,))
        components = cursor.fetchall()
        conn.close()
        return components
    
    def get_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM components')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM components WHERE quantity < 5 AND needs_restock = 0')
        low = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM components WHERE needs_restock = 1')
        shopping = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM projects')
        projects = cursor.fetchone()[0]
        conn.close()
        return total, low, shopping, projects

# ============ ROUNDED BUTTON ============
class RoundedButton(Button):
    def __init__(self, bg_color='#4F46E5', text_color='#FFFFFF', radius=15, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = get_color_from_hex(bg_color)
        self.radius = dp(radius)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = get_color_from_hex(text_color)
        
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            self.bind(pos=self._update_rect, size=self._update_rect)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def set_bg(self, color_hex):
        self.bg_color = get_color_from_hex(color_hex)
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            self.bind(pos=self._update_rect, size=self._update_rect)

# ============ COLOR BAND ============
class ColorBand(BoxLayout):
    def __init__(self, color_name, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(35)
        color_hex = COLOR_HEX.get(color_name.lower(), '#CCCCCC')
        with self.canvas.before:
            Color(*hex_to_rgb(color_hex))
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
            self.bind(pos=self._update_rect, size=self._update_rect)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

# ============ COMPONENT CARD ============
class ComponentCard(BoxLayout):
    def __init__(self, component, app, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(135)
        self.padding = dp(15)
        self.spacing = dp(5)
        self.opacity = 0
        
        comp_id, comp_type, name, value, qty, location, notes, tolerance, wattage, cap_type, voltage, needs_restock, created = component
        
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)])
            self.bind(pos=self._update_rect, size=self._update_rect)
        
        top_row = BoxLayout(size_hint_y=0.25, spacing=dp(8))
        
        type_badge = RoundedButton(
            text=comp_type.upper(),
            bg_color=TYPE_COLORS.get(comp_type, '#6B7280'),
            text_color='#FFFFFF',
            radius=10,
            size_hint_x=0.4,
            font_size=dp(9),
            bold=True
        )
        
        edit_btn = RoundedButton(
            text='✏️',
            bg_color='#E5E7EB',
            text_color='#374151',
            radius=10,
            size_hint_x=0.15
        )
        edit_btn.bind(on_press=lambda x: app.show_edit_dialog(comp_id))
        
        star_text = '⭐' if needs_restock else '☆'
        star_btn = RoundedButton(
            text=star_text,
            bg_color='#FEF3C7' if needs_restock else '#F3F4F6',
            text_color='#92400E' if needs_restock else '#6B7280',
            radius=10,
            size_hint_x=0.15
        )
        star_btn.bind(on_press=lambda x: app.toggle_restock(comp_id))
        
        delete_btn = RoundedButton(
            text='🗑',
            bg_color='#FEE2E2',
            text_color='#991B1B',
            radius=10,
            size_hint_x=0.15
        )
        delete_btn.bind(on_press=lambda x: app.delete_component(comp_id))
        
        top_row.add_widget(type_badge)
        top_row.add_widget(edit_btn)
        top_row.add_widget(star_btn)
        top_row.add_widget(delete_btn)
        
        name_label = Label(text=name, font_size=dp(14), bold=True, size_hint_y=0.2, halign='left', valign='middle')
        name_label.color = get_color_from_hex('#111827')
        
        value_label = Label(text=value or '', font_size=dp(12), size_hint_y=0.18, halign='left', valign='middle')
        value_label.color = get_color_from_hex('#4F46E5')
        
        details = f'📦 {qty}'
        if location:
            details += f'   📍 {location}'
        detail_label = Label(text=details, font_size=dp(9), size_hint_y=0.12, halign='left')
        detail_label.color = get_color_from_hex('#6B7280')
        
        self.add_widget(top_row)
        self.add_widget(name_label)
        self.add_widget(value_label)
        self.add_widget(detail_label)
        
        if comp_type == 'resistor' and value:
            resistance = parse_resistance(value)
            if resistance:
                colors = get_resistor_colors(resistance, tolerance)
                if colors:
                    bands_row = BoxLayout(size_hint_y=0.12, spacing=dp(4), padding=[dp(5), dp(10), dp(5), dp(5)])
                    for color_name in colors:
                        bands_row.add_widget(ColorBand(color_name))
                    self.add_widget(bands_row)
                    self.height = dp(160)
        
        if comp_type == 'capacitor' and value:
            capacitance = parse_capacitance(value)
            if capacitance:
                code = get_capacitor_code(capacitance)
                if code:
                    code_label = Label(text=f'Code: {code}', font_size=dp(10), size_hint_y=0.12, halign='left')
                    code_label.color = get_color_from_hex('#DC2626')
                    self.add_widget(code_label)
                    self.height = dp(160)
        
        anim = Animation(opacity=1, duration=0.3)
        anim.start(self)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

# ============ RESISTOR CALCULATOR ============
class ResistorCalculator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(15)
        self.spacing = dp(10)
        
        title = Label(text='Resistor Color Code Calculator', font_size=dp(16), bold=True, halign='left')
        title.color = get_color_from_hex('#111827')
        self.add_widget(title)
        
        self.add_widget(Label(text='Number of Bands:', halign='left', size_hint_y=None, height=dp(15), color=get_color_from_hex('#6B7280')))
        self.band_count = Spinner(text='4 Bands', values=['4 Bands', '5 Bands', '6 Bands'], size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#FFFFFF'))
        self.band_count.bind(text=self.on_band_count_change)
        self.add_widget(self.band_count)
        
        band_colors = ['Black', 'Brown', 'Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Violet', 'Gray', 'White']
        multiplier_colors = ['Black', 'Brown', 'Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Gold', 'Silver']
        tolerance_colors = ['Brown', 'Red', 'Green', 'Blue', 'Violet', 'Gold', 'Silver', 'None']
        
        self.add_widget(Label(text='Band 1:', halign='left', size_hint_y=None, height=dp(15), color=get_color_from_hex('#6B7280')))
        self.band1 = Spinner(text='Brown', values=band_colors, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#FFFFFF'))
        self.add_widget(self.band1)
        
        self.add_widget(Label(text='Band 2:', halign='left', size_hint_y=None, height=dp(15), color=get_color_from_hex('#6B7280')))
        self.band2 = Spinner(text='Black', values=band_colors, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#FFFFFF'))
        self.add_widget(self.band2)
        
        self.band3_label = Label(text='Band 3:', halign='left', size_hint_y=None, height=dp(15), color=get_color_from_hex('#6B7280'))
        self.band3 = Spinner(text='Black', values=band_colors, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#FFFFFF'))
        
        self.mult_label = Label(text='Multiplier:', halign='left', size_hint_y=None, height=dp(15), color=get_color_from_hex('#6B7280'))
        self.add_widget(self.mult_label)
        self.multiplier = Spinner(text='Brown', values=multiplier_colors, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#FFFFFF'))
        self.add_widget(self.multiplier)
        
        self.tol_label = Label(text='Tolerance:', halign='left', size_hint_y=None, height=dp(15), color=get_color_from_hex('#6B7280'))
        self.add_widget(self.tol_label)
        self.tolerance = Spinner(text='Gold', values=tolerance_colors, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#FFFFFF'))
        self.add_widget(self.tolerance)
        
        calc_btn = RoundedButton(text='Calculate', bg_color='#4F46E5', text_color='#FFFFFF', radius=15, size_hint_y=None, height=dp(50), bold=True)
        calc_btn.bind(on_press=self.calculate)
        self.add_widget(calc_btn)
        
        self.result_label = Label(text='Select colors and tap Calculate', font_size=dp(14), halign='center', size_hint_y=None, height=dp(50))
        self.result_label.color = get_color_from_hex('#4F46E5')
        self.add_widget(self.result_label)
        
        self.color_display = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        self.add_widget(self.color_display)
    
    def on_band_count_change(self, spinner, text):
        if text == '4 Bands':
            if self.band3_label.parent:
                self.remove_widget(self.band3_label)
                self.remove_widget(self.band3)
        else:
            if not self.band3_label.parent:
                self.add_widget(self.band3_label, index=4)
                self.add_widget(self.band3, index=5)
    
    def calculate(self, instance):
        color_values = {'Black': 0, 'Brown': 1, 'Red': 2, 'Orange': 3, 'Yellow': 4,
                       'Green': 5, 'Blue': 6, 'Violet': 7, 'Gray': 8, 'White': 9}
        multiplier_values = {'Black': 1, 'Brown': 10, 'Red': 100, 'Orange': 1000,
                           'Yellow': 10000, 'Green': 100000, 'Blue': 1000000,
                           'Gold': 0.1, 'Silver': 0.01}
        
        if self.band_count.text == '4 Bands':
            digit1 = color_values[self.band1.text]
            digit2 = color_values[self.band2.text]
            mult = multiplier_values[self.multiplier.text]
            resistance = (digit1 * 10 + digit2) * mult
            color_names = [self.band1.text, self.band2.text, self.multiplier.text, self.tolerance.text]
        else:
            digit1 = color_values[self.band1.text]
            digit2 = color_values[self.band2.text]
            digit3 = color_values[self.band3.text]
            mult = multiplier_values[self.multiplier.text]
            resistance = (digit1 * 100 + digit2 * 10 + digit3) * mult
            color_names = [self.band1.text, self.band2.text, self.band3.text, self.multiplier.text, self.tolerance.text]
        
        if resistance >= 1000000:
            result = f'{resistance/1000000:.1f} MΩ'
        elif resistance >= 1000:
            result = f'{resistance/1000:.1f} kΩ'
        else:
            result = f'{resistance:.0f} Ω'
        
        self.result_label.text = f'{result}\n{", ".join(color_names)}'
        
        self.color_display.clear_widgets()
        for color_name in color_names:
            self.color_display.add_widget(ColorBand(color_name))
    
    def _update_band(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size

# ============ MAIN APP ============
class ComponentInventoryApp(App):
    def build(self):
        self.db = Database()
        self.title = 'Component Inventory'
        
        self.main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        title_label = Label(text='⚡ Component Inventory', font_size=dp(20), bold=True, size_hint_y=None, height=dp(40))
        title_label.color = get_color_from_hex('#111827')
        self.main_layout.add_widget(title_label)
        
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        
        self.tab_buttons = {}
        tab_configs = [
            ('Dashboard', '📊'),
            ('Components', '📦'),
            ('Projects', '🔧'),
            ('Calculator', '🧮')
        ]
        
        for tab_name, icon in tab_configs:
            btn = RoundedButton(text=f'{icon} {tab_name}', bg_color='#E5E7EB', text_color='#374151', radius=15, font_size=dp(13))
            btn.bind(on_press=self.switch_tab)
            self.tab_buttons[tab_name] = btn
            self.tab_bar.add_widget(btn)
        
        self.main_layout.add_widget(self.tab_bar)
        
        self.content_area = BoxLayout(orientation='vertical')
        self.main_layout.add_widget(self.content_area)
        
        self.build_dashboard_tab()
        self.build_components_tab()
        self.build_projects_tab()
        self.build_calculator_tab()
        
        self.switch_tab(self.tab_buttons['Dashboard'])
        
        return self.main_layout
    
    def switch_tab(self, instance):
        for btn in self.tab_buttons.values():
            btn.set_bg('#E5E7EB')
            btn.color = get_color_from_hex('#374151')
        
        instance.set_bg('#4F46E5')
        instance.color = get_color_from_hex('#FFFFFF')
        
        self.content_area.clear_widgets()
        self.content_area.opacity = 0
        anim = Animation(opacity=1, duration=0.2)
        
        if instance.text == '📊 Dashboard':
            self.content_area.add_widget(self.dashboard_layout)
            self.load_dashboard()
        elif instance.text == '📦 Components':
            self.content_area.add_widget(self.components_layout)
            self.load_components()
        elif instance.text == '🔧 Projects':
            self.content_area.add_widget(self.projects_layout)
            self.load_projects()
        elif instance.text == '🧮 Calculator':
            self.content_area.add_widget(self.calculator_layout)
        
        anim.start(self.content_area)
    
    def build_dashboard_tab(self):
        self.dashboard_layout = ScrollView()
        self.dashboard_content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(10), size_hint_y=None)
        self.dashboard_content.bind(minimum_height=self.dashboard_content.setter('height'))
        self.dashboard_layout.add_widget(self.dashboard_content)
    
    def build_components_tab(self):
        self.components_layout = BoxLayout(orientation='vertical', spacing=dp(8))
        
        self.search_input = TextInput(hint_text='Search components...', size_hint_y=None, height=dp(40), multiline=False, background_color=get_color_from_hex('#FFFFFF'), padding=[dp(10), dp(5)])
        self.search_input.bind(text=self.on_search)
        
        self.type_filter = Spinner(text='All Types', values=['All Types'] + COMPONENT_TYPES, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#FFFFFF'))
        self.type_filter.bind(text=self.on_filter)
        
        self.components_scroll = ScrollView()
        self.components_grid = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.components_grid.bind(minimum_height=self.components_grid.setter('height'))
        self.components_scroll.add_widget(self.components_grid)
        
        add_btn = RoundedButton(text='+ Add Component', bg_color='#4F46E5', text_color='#FFFFFF', radius=15, size_hint_y=None, height=dp(50), bold=True)
        add_btn.bind(on_press=self.show_add_dialog)
        
        self.components_layout.add_widget(self.search_input)
        self.components_layout.add_widget(self.type_filter)
        self.components_layout.add_widget(self.components_scroll)
        self.components_layout.add_widget(add_btn)
    
    def build_projects_tab(self):
        self.projects_layout = BoxLayout(orientation='vertical', spacing=dp(8))
        
        self.projects_scroll = ScrollView()
        self.projects_grid = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.projects_grid.bind(minimum_height=self.projects_grid.setter('height'))
        self.projects_scroll.add_widget(self.projects_grid)
        
        add_project_btn = RoundedButton(text='+ New Project', bg_color='#4F46E5', text_color='#FFFFFF', radius=15, size_hint_y=None, height=dp(50), bold=True)
        add_project_btn.bind(on_press=self.show_add_project_dialog)
        
        self.projects_layout.add_widget(self.projects_scroll)
        self.projects_layout.add_widget(add_project_btn)
    
    def build_calculator_tab(self):
        self.calculator_layout = ScrollView()
        self.calculator = ResistorCalculator()
        self.calculator_layout.add_widget(self.calculator)
    
    def on_search(self, instance, value):
        self.load_components()
    
    def on_filter(self, instance, value):
        self.load_components()
    
    def load_dashboard(self):
        self.dashboard_content.clear_widgets()
        
        total, low, shopping, projects = self.db.get_stats()
        
        stats_card = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(130), padding=dp(15), spacing=dp(8))
        with stats_card.canvas.before:
            Color(*hex_to_rgb('#4F46E5'))
            stats_card.rect = RoundedRectangle(pos=stats_card.pos, size=stats_card.size, radius=[dp(15)])
            stats_card.bind(pos=self._update_rect, size=self._update_rect)
        
        stats_title = Label(text='📊 Statistics', font_size=dp(16), bold=True, size_hint_y=0.25, halign='left')
        stats_title.color = get_color_from_hex('#FFFFFF')
        
        stats_text = Label(
            text=f'Total Components: {total}\nLow Stock: {low}\nShopping List: {shopping}\nProjects: {projects}',
            font_size=dp(13),
            size_hint_y=0.75,
            halign='left'
        )
        stats_text.color = get_color_from_hex('#FFFFFF')
        
        stats_card.add_widget(stats_title)
        stats_card.add_widget(stats_text)
        self.dashboard_content.add_widget(stats_card)
        
        low_label = Label(text='⚠️ Low Stock', font_size=dp(16), bold=True, size_hint_y=None, height=dp(30), halign='left')
        low_label.color = get_color_from_hex('#111827')
        self.dashboard_content.add_widget(low_label)
        
        low_stock_items = self.db.get_low_stock()
        if not low_stock_items:
            no_low = Label(text='No low stock items! 🎉', font_size=dp(13), size_hint_y=None, height=dp(40), halign='left')
            no_low.color = get_color_from_hex('#9CA3AF')
            self.dashboard_content.add_widget(no_low)
        else:
            for comp in low_stock_items:
                card = ComponentCard(comp, self)
                self.dashboard_content.add_widget(card)
        
        shop_label = Label(text='🛒 Shopping List', font_size=dp(16), bold=True, size_hint_y=None, height=dp(30), halign='left')
        shop_label.color = get_color_from_hex('#111827')
        self.dashboard_content.add_widget(shop_label)
        
        shop_items = self.db.get_shopping_list()
        if not shop_items:
            no_shop = Label(text='Shopping list empty\nTap ☆ on components to add them here', font_size=dp(13), size_hint_y=None, height=dp(50), halign='left')
            no_shop.color = get_color_from_hex('#9CA3AF')
            self.dashboard_content.add_widget(no_shop)
        else:
            for comp in shop_items:
                card = ComponentCard(comp, self)
                self.dashboard_content.add_widget(card)
    
    def _update_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size
    
    def load_components(self):
        self.components_grid.clear_widgets()
        
        search = self.search_input.text
        type_filter = ''
        if self.type_filter.text != 'All Types':
            type_filter = self.type_filter.text.lower()
        
        components = self.db.get_components(search, type_filter)
        
        if not components:
            empty_label = Label(text='No components found\nTap + to add', font_size=dp(15), halign='center')
            empty_label.color = get_color_from_hex('#9CA3AF')
            self.components_grid.add_widget(empty_label)
        else:
            for comp in components:
                card = ComponentCard(comp, self)
                self.components_grid.add_widget(card)
    
    def load_projects(self):
        self.projects_grid.clear_widgets()
        
        projects = self.db.get_projects()
        
        if not projects:
            empty_label = Label(text='No projects yet\nTap + to create', font_size=dp(15), halign='center')
            empty_label.color = get_color_from_hex('#9CA3AF')
            self.projects_grid.add_widget(empty_label)
        else:
            for proj in projects:
                proj_id, name, desc, status, created = proj
                proj_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100), padding=dp(12), spacing=dp(5))
                
                with proj_box.canvas.before:
                    Color(1, 1, 1, 1)
                    proj_box.rect = RoundedRectangle(pos=proj_box.pos, size=proj_box.size, radius=[dp(15)])
                    proj_box.bind(pos=self._update_rect, size=self._update_rect)
                
                name_label = Label(text=name, font_size=dp(14), bold=True, size_hint_y=0.25, halign='left')
                name_label.color = get_color_from_hex('#111827')
                
                status_label = Label(text=status, font_size=dp(10), size_hint_y=0.15, halign='left')
                status_label.color = get_color_from_hex('#6B7280')
                
                proj_comps = self.db.get_project_components(proj_id)
                if proj_comps:
                    comps_text = ', '.join([f'{pc[2]} x{pc[1]}' for pc in proj_comps])
                else:
                    comps_text = 'No components added'
                comps_label = Label(text=comps_text, font_size=dp(9), size_hint_y=0.3, halign='left')
                comps_label.color = get_color_from_hex('#4F46E5')
                
                delete_btn = RoundedButton(text='Delete', bg_color='#FEE2E2', text_color='#991B1B', radius=10, size_hint_y=0.2, font_size=dp(10))
                delete_btn.bind(on_press=lambda x, pid=proj_id: self.delete_project(pid))
                
                proj_box.add_widget(name_label)
                proj_box.add_widget(status_label)
                proj_box.add_widget(comps_label)
                proj_box.add_widget(delete_btn)
                
                self.projects_grid.add_widget(proj_box)
    
    def show_add_dialog(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        
        type_spinner = Spinner(text='Resistor', values=COMPONENT_TYPES, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#F3F4F6'))
        
        name_input = TextInput(hint_text='Name', multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        value_input = TextInput(hint_text='Value', multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        qty_input = TextInput(hint_text='Quantity', multiline=False, input_filter='int', size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        location_input = TextInput(hint_text='Location (optional)', multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        
        value_spinner = Spinner(text='Quick Select', values=RESISTOR_VALUES, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#F3F4F6'))
        
        self.color_preview = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(5))
        
        def on_value_select(spinner, text):
            value_input.text = text
            self.update_color_preview(type_spinner.text, text)
        
        value_spinner.bind(text=on_value_select)
        
        def on_type_select(spinner, text):
            if text == 'Resistor':
                value_spinner.values = RESISTOR_VALUES
            elif text == 'Capacitor':
                value_spinner.values = CAPACITOR_VALUES
            else:
                value_spinner.values = []
            self.update_color_preview(text, value_input.text)
        
        type_spinner.bind(text=on_type_select)
        
        def on_value_text(instance, value):
            self.update_color_preview(type_spinner.text, value)
        
        value_input.bind(text=on_value_text)
        
        save_btn = RoundedButton(text='Save', bg_color='#4F46E5', text_color='#FFFFFF', radius=15, size_hint_y=None, height=dp(50), bold=True)
        
        content.add_widget(type_spinner)
        content.add_widget(name_input)
        content.add_widget(value_spinner)
        content.add_widget(value_input)
        content.add_widget(qty_input)
        content.add_widget(location_input)
        content.add_widget(Label(text='Color Code Preview:', halign='left', size_hint_y=None, height=dp(20), color=get_color_from_hex('#6B7280')))
        content.add_widget(self.color_preview)
        content.add_widget(save_btn)
        
        popup = Popup(title='Add Component', content=content, size_hint=(0.9, 0.8))
        
        def save(instance):
            if not name_input.text:
                return
            
            comp_data = {
                'type': type_spinner.text.lower(),
                'name': name_input.text,
                'value': value_input.text,
                'quantity': int(qty_input.text or 0),
                'location': location_input.text
            }
            
            self.db.add_component(comp_data)
            popup.dismiss()
            self.load_components()
            self.load_dashboard()
        
        save_btn.bind(on_press=save)
        popup.open()
    
    def show_edit_dialog(self, comp_id):
        component = self.db.get_component(comp_id)
        if not component:
            return
        
        comp_id, comp_type, name, value, qty, location, notes, tolerance, wattage, cap_type, voltage, needs_restock, created = component
        
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        
        type_spinner = Spinner(text=comp_type.capitalize(), values=COMPONENT_TYPES, size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#F3F4F6'))
        
        name_input = TextInput(text=name, multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        value_input = TextInput(text=value or '', multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        qty_input = TextInput(text=str(qty), multiline=False, input_filter='int', size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        location_input = TextInput(text=location or '', multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        
        save_btn = RoundedButton(text='Update', bg_color='#4F46E5', text_color='#FFFFFF', radius=15, size_hint_y=None, height=dp(50), bold=True)
        
        content.add_widget(type_spinner)
        content.add_widget(name_input)
        content.add_widget(value_input)
        content.add_widget(qty_input)
        content.add_widget(location_input)
        content.add_widget(save_btn)
        
        popup = Popup(title='Edit Component', content=content, size_hint=(0.9, 0.6))
        
        def update(instance):
            if not name_input.text:
                return
            
            comp_data = {
                'type': type_spinner.text.lower(),
                'name': name_input.text,
                'value': value_input.text,
                'quantity': int(qty_input.text or 0),
                'location': location_input.text
            }
            
            self.db.update_component(comp_id, comp_data)
            popup.dismiss()
            self.load_components()
            self.load_dashboard()
        
        save_btn.bind(on_press=update)
        popup.open()
    
    def update_color_preview(self, comp_type, value):
        self.color_preview.clear_widgets()
        
        if comp_type == 'Resistor' and value:
            resistance = parse_resistance(value)
            if resistance:
                colors = get_resistor_colors(resistance)
                if colors:
                    for color_name in colors:
                        self.color_preview.add_widget(ColorBand(color_name))
        elif comp_type == 'Capacitor' and value:
            capacitance = parse_capacitance(value)
            if capacitance:
                code = get_capacitor_code(capacitance)
                if code:
                    code_label = Label(text=code, font_size=dp(14), bold=True, halign='left')
                    code_label.color = get_color_from_hex('#DC2626')
                    self.color_preview.add_widget(code_label)
    
    def show_add_project_dialog(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        
        name_input = TextInput(hint_text='Project name', multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        desc_input = TextInput(hint_text='Description (optional)', multiline=False, size_hint_y=None, height=dp(40), halign='left', background_color=get_color_from_hex('#FFFFFF'))
        
        status_spinner = Spinner(text='Planning', values=['Planning', 'In Progress', 'Completed', 'On Hold'], size_hint_y=None, height=dp(40), background_color=get_color_from_hex('#F3F4F6'))
        
        components_label = Label(text='Components Needed:', halign='left', size_hint_y=None, height=dp(20))
        components_label.color = get_color_from_hex('#6B7280')
        
        components_container = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(40), spacing=dp(5))
        
        def add_component_row(instance):
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
            
            all_comps = self.db.get_components()
            comp_options = ['Select...'] + [f'{c[0]}: {c[1]} - {c[2] or ""}' for c in all_comps]
            
            comp_spinner = Spinner(text='Select...', values=comp_options, size_hint_x=0.7, background_color=get_color_from_hex('#FFFFFF'))
            qty_input = TextInput(text='1', multiline=False, input_filter='int', size_hint_x=0.3, halign='center', background_color=get_color_from_hex('#FFFFFF'))
            
            row.add_widget(comp_spinner)
            row.add_widget(qty_input)
            components_container.add_widget(row)
            components_container.height += dp(45)
        
        add_comp_btn = RoundedButton(text='+ Add Component', bg_color='#E5E7EB', text_color='#374151', radius=10, size_hint_y=None, height=dp(35))
        add_comp_btn.bind(on_press=add_component_row)
        
        save_btn = RoundedButton(text='Save Project', bg_color='#4F46E5', text_color='#FFFFFF', radius=15, size_hint_y=None, height=dp(50), bold=True)
        
        content.add_widget(name_input)
        content.add_widget(desc_input)
        content.add_widget(status_spinner)
        content.add_widget(components_label)
        content.add_widget(components_container)
        content.add_widget(add_comp_btn)
        content.add_widget(save_btn)
        
        popup = Popup(title='New Project', content=content, size_hint=(0.9, 0.75))
        
        def save(instance):
            if not name_input.text:
                return
            
            project_id = self.db.add_project(name_input.text, desc_input.text, status_spinner.text)
            
            for child in components_container.children:
                if isinstance(child, BoxLayout):
                    comp_spinner = child.children[1]
                    qty_input = child.children[0]
                    selected = comp_spinner.text
                    if selected != 'Select...':
                        comp_id = int(selected.split(':')[0])
                        qty = int(qty_input.text or 1)
                        self.db.add_component_to_project(project_id, comp_id, qty)
            
            popup.dismiss()
            self.load_projects()
            self.load_dashboard()
        
        save_btn.bind(on_press=save)
        popup.open()
    
    def toggle_restock(self, comp_id):
        self.db.toggle_restock(comp_id)
        self.load_components()
        self.load_dashboard()
    
    def delete_component(self, comp_id):
        self.db.delete_component(comp_id)
        self.load_components()
        self.load_dashboard()
    
    def delete_project(self, proj_id):
        self.db.delete_project(proj_id)
        self.load_projects()
        self.load_dashboard()

if __name__ == '__main__':
    ComponentInventoryApp().run()