"""
HTML Table Extractor - Extract structured tables from web pages.

This extracts comparison tables, spec sheets, price lists automatically.
"""
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass
import re


@dataclass
class ExtractedTable:
    """An extracted HTML table."""
    headers: List[str]
    rows: List[List[str]]
    caption: str = ""
    source_url: str = ""
    
    def to_dict_list(self) -> List[Dict[str, str]]:
        """Convert table to list of dictionaries."""
        result = []
        for row in self.rows:
            row_dict = {}
            for i, header in enumerate(self.headers):
                if i < len(row):
                    row_dict[header] = row[i]
            if row_dict:
                result.append(row_dict)
        return result


class TableExtractor:
    """
    Extracts structured tables from HTML content.
    
    Finds:
    - Comparison tables
    - Specification tables
    - Price lists
    - Feature matrices
    """
    
    def __init__(self):
        self.min_rows = 2
        self.min_cols = 2
        self.max_tables = 5
    
    def extract_tables(self, html: str, source_url: str = "") -> List[ExtractedTable]:
        """
        Extract all tables from HTML.
        
        Args:
            html: HTML content
            source_url: Source URL for context
        
        Returns:
            List of ExtractedTable objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        tables = []
        
        for table_elem in soup.find_all('table')[:self.max_tables]:
            table = self._parse_table(table_elem, source_url)
            if table and len(table.rows) >= self.min_rows:
                tables.append(table)
        
        # Also try to find structured div-based tables (common in modern sites)
        div_tables = self._extract_div_tables(soup, source_url)
        tables.extend(div_tables)
        
        return tables
    
    def _parse_table(self, table_elem, source_url: str) -> Optional[ExtractedTable]:
        """Parse a single table element."""
        # Get caption
        caption = ""
        caption_elem = table_elem.find('caption')
        if caption_elem:
            caption = caption_elem.get_text(strip=True)
        
        # Get headers
        headers = []
        header_row = table_elem.find('thead')
        if header_row:
            th_cells = header_row.find_all('th')
            headers = [cell.get_text(strip=True) for cell in th_cells]
        
        # If no thead, try first row
        if not headers:
            first_row = table_elem.find('tr')
            if first_row:
                th_cells = first_row.find_all('th')
                if th_cells:
                    headers = [cell.get_text(strip=True) for cell in th_cells]
                else:
                    # First row might be headers in td cells
                    td_cells = first_row.find_all('td')
                    if td_cells:
                        headers = [cell.get_text(strip=True) for cell in td_cells]
        
        if not headers:
            return None
        
        # Get data rows
        rows = []
        tbody = table_elem.find('tbody')
        row_elements = tbody.find_all('tr') if tbody else table_elem.find_all('tr')[1:]  # Skip header
        
        for row in row_elements:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data and any(cell for cell in row_data):  # Skip empty rows
                rows.append(row_data)
        
        if len(rows) < self.min_rows:
            return None
        
        return ExtractedTable(
            headers=headers,
            rows=rows,
            caption=caption,
            source_url=source_url
        )
    
    def _extract_div_tables(self, soup: BeautifulSoup, source_url: str) -> List[ExtractedTable]:
        """
        Extract div-based tables (common in React/Vue sites).
        
        Looks for grid layouts that might be comparison tables.
        """
        tables = []
        
        # Look for common table-like div structures
        selectors = [
            '.comparison-table',
            '.specs-table',
            '.product-table',
            '.pricing-table',
            '[class*="table"]',
            '[class*="comparison"]',
            '[class*="specs"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements[:2]:  # Limit per selector
                table = self._try_parse_div_table(elem, source_url)
                if table:
                    tables.append(table)
        
        return tables
    
    def _try_parse_div_table(self, elem, source_url: str) -> Optional[ExtractedTable]:
        """Try to parse a div structure as a table."""
        # Look for row-like structures
        row_selectors = ['.row', '[class*="row"]', '> div']
        
        rows = []
        headers = []
        
        for selector in row_selectors:
            row_elements = elem.select(selector)
            if len(row_elements) >= 2:
                # First row might be headers
                first_row = row_elements[0]
                header_cells = first_row.select('.col, [class*="col"], > div')
                if not headers and header_cells:
                    headers = [cell.get_text(strip=True) for cell in header_cells]
                
                # Data rows
                for row_elem in row_elements[1:]:
                    cells = row_elem.select('.col, [class*="col"], > div')
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    if row_data:
                        rows.append(row_data)
                
                if headers and len(rows) >= self.min_rows:
                    return ExtractedTable(
                        headers=headers,
                        rows=rows,
                        source_url=source_url
                    )
        
        return None
    
    def find_comparison_tables(self, html: str, keywords: List[str], source_url: str = "") -> List[ExtractedTable]:
        """
        Find tables that appear to be comparisons.
        
        Args:
            html: HTML content
            keywords: Keywords to look for (e.g., ["price", "specs"])
            source_url: Source URL
        
        Returns:
            List of comparison tables
        """
        all_tables = self.extract_tables(html, source_url)
        comparison_tables = []
        
        for table in all_tables:
            # Check if headers contain comparison keywords
            header_text = ' '.join(table.headers).lower()
            
            # Score the table
            score = 0
            for keyword in keywords:
                if keyword.lower() in header_text:
                    score += 1
            
            # Check caption
            if table.caption:
                caption_lower = table.caption.lower()
                if any(word in caption_lower for word in ["comparison", "vs", "versus", "best", "top"]):
                    score += 2
            
            if score >= 2 or len(table.rows) >= 5:  # Good table or many rows
                comparison_tables.append(table)
        
        return comparison_tables
    
    def merge_similar_tables(self, tables: List[ExtractedTable]) -> List[ExtractedTable]:
        """
        Merge tables that appear to be the same structure.
        
        Useful when a table is split across multiple pages.
        """
        if not tables:
            return []
        
        merged = []
        used = set()
        
        for i, table1 in enumerate(tables):
            if i in used:
                continue
            
            similar_tables = [table1]
            used.add(i)
            
            for j, table2 in enumerate(tables[i+1:], i+1):
                if j in used:
                    continue
                
                # Check if headers match
                if table1.headers == table2.headers:
                    similar_tables.append(table2)
                    used.add(j)
            
            # Merge rows
            all_rows = []
            for t in similar_tables:
                all_rows.extend(t.rows)
            
            merged.append(ExtractedTable(
                headers=table1.headers,
                rows=all_rows,
                caption=table1.caption,
                source_url=table1.source_url
            ))
        
        return merged


def get_table_extractor() -> TableExtractor:
    """Factory function."""
    return TableExtractor()
