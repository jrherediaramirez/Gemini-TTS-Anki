# -*- coding: utf-8 -*-
"""
Content Analysis for Intelligent TTS Preprocessing
=================================================

Analyzes text structure to optimize Gemini TTS preprocessing.
Detects bullet points, lists, content types, and suggests optimal processing strategies.
"""

import re
from typing import Dict, List, Any, Tuple

class ContentAnalyzer:
    """Analyze text structure for optimal TTS preprocessing"""
    
    def __init__(self):
        """Initialize content analyzer with pattern matchers"""
        self.bullet_patterns = [
            r'^[\s]*[•·‣⁃▪▫‧◦⦾⦿]\s*',
            r'^[\s]*[-*+]\s*',
            r'^[\s]*\d+[.)]\s*',
            r'^[\s]*[a-zA-Z][.)]\s*',
            r'^[\s]*[ivxlcdm]+[.)]\s*',  # Roman numerals
        ]
        
        self.step_indicators = [
            'first', 'second', 'third', 'next', 'then', 'finally',
            'step', 'stage', 'phase', 'install', 'configure', 'setup'
        ]
        
        self.feature_indicators = [
            'feature', 'benefit', 'advantage', 'capability', 'includes',
            'offers', 'provides', 'supports', 'enables'
        ]
        
        self.option_indicators = [
            'option', 'choice', 'alternative', 'can', 'may', 'either',
            'plan', 'package', 'version', 'tier'
        ]
    
    def analyze_structure(self, text: str) -> Dict[str, Any]:
        """Comprehensive content structure analysis"""
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        analysis = {
            "type": self._detect_content_type(text, cleaned_lines),
            "has_bullets": self._has_bullet_points(cleaned_lines),
            "has_numbers": self._has_numbered_lists(cleaned_lines),
            "line_count": len(cleaned_lines),
            "avg_line_length": self._calculate_avg_line_length(cleaned_lines),
            "complexity": self._assess_complexity(text, cleaned_lines),
            "suggested_thinking_budget": self._suggest_thinking_budget(text, cleaned_lines),
            "preprocessing_strategy": self._suggest_preprocessing_strategy(text, cleaned_lines),
            "estimated_speech_time": self._estimate_speech_time(text)
        }
        
        return analysis
    
    def _detect_content_type(self, text: str, lines: List[str]) -> str:
        """Classify content type for appropriate preprocessing"""
        text_lower = text.lower()
        
        # Check for step-by-step instructions
        step_score = sum(1 for indicator in self.step_indicators if indicator in text_lower)
        if step_score >= 2 or any('step' in line.lower() for line in lines[:3]):
            return "instructions"
        
        # Check for feature/benefit lists
        feature_score = sum(1 for indicator in self.feature_indicators if indicator in text_lower)
        if feature_score >= 2:
            return "features"
        
        # Check for options/choices
        option_score = sum(1 for indicator in self.option_indicators if indicator in text_lower)
        if option_score >= 2:
            return "options"
        
        # Check for technical content
        if self._is_technical_content(text):
            return "technical"
        
        # Check for Q&A format
        if '?' in text and any(line.endswith('?') for line in lines):
            return "qa"
        
        # Default to general content
        return "general"
    
    def _has_bullet_points(self, lines: List[str]) -> bool:
        """Check if text contains bullet points"""
        bullet_count = 0
        for line in lines:
            for pattern in self.bullet_patterns:
                if re.match(pattern, line):
                    bullet_count += 1
                    break
        
        return bullet_count >= 2
    
    def _has_numbered_lists(self, lines: List[str]) -> bool:
        """Check if text contains numbered lists"""
        numbered_pattern = r'^[\s]*\d+[.)]\s*'
        numbered_count = sum(1 for line in lines if re.match(numbered_pattern, line))
        return numbered_count >= 2
    
    def _calculate_avg_line_length(self, lines: List[str]) -> float:
        """Calculate average line length"""
        if not lines:
            return 0.0
        return sum(len(line) for line in lines) / len(lines)
    
    def _assess_complexity(self, text: str, lines: List[str]) -> str:
        """Assess text complexity for processing strategy"""
        # Simple metrics for complexity assessment
        char_count = len(text)
        line_count = len(lines)
        avg_line_length = self._calculate_avg_line_length(lines)
        
        # Count complex elements
        has_nested_structure = any('  ' in line for line in lines)  # Indented content
        has_special_chars = bool(re.search(r'[{}()\[\]<>]', text))
        has_technical_terms = self._is_technical_content(text)
        
        complexity_score = 0
        
        if char_count > 1000:
            complexity_score += 2
        elif char_count > 500:
            complexity_score += 1
        
        if line_count > 10:
            complexity_score += 1
        
        if avg_line_length > 100:
            complexity_score += 1
        
        if has_nested_structure:
            complexity_score += 1
        
        if has_special_chars:
            complexity_score += 1
        
        if has_technical_terms:
            complexity_score += 2
        
        if complexity_score >= 5:
            return "high"
        elif complexity_score >= 3:
            return "medium"
        else:
            return "low"
    
    def _is_technical_content(self, text: str) -> bool:
        """Detect technical content that needs special handling"""
        technical_indicators = [
            'api', 'http', 'url', 'json', 'xml', 'sql', 'css', 'html',
            'function', 'class', 'method', 'variable', 'parameter',
            'config', 'settings', 'database', 'server', 'client',
            'algorithm', 'code', 'syntax', 'compile', 'debug'
        ]
        
        text_lower = text.lower()
        technical_score = sum(1 for term in technical_indicators if term in text_lower)
        
        # Also check for code-like patterns
        has_code_patterns = bool(re.search(r'[{}()\[\]<>]|[a-zA-Z_][a-zA-Z0-9_]*\(', text))
        
        return technical_score >= 3 or has_code_patterns
    
    def _suggest_thinking_budget(self, text: str, lines: List[str]) -> int:
        """Suggest optimal thinking budget based on complexity"""
        complexity = self._assess_complexity(text, lines)
        content_type = self._detect_content_type(text, lines)
        has_structure = self._has_bullet_points(lines) or self._has_numbered_lists(lines)
        
        # Base budget on complexity
        if complexity == "high":
            base_budget = 512
        elif complexity == "medium":
            base_budget = 256
        else:
            base_budget = 0  # Simple content doesn't need thinking
        
        # Adjust based on content type
        if content_type in ["instructions", "technical"]:
            base_budget += 256
        elif content_type in ["features", "options"]:
            base_budget += 128
        
        # Adjust for structured content
        if has_structure:
            base_budget += 128
        
        # Cap at reasonable maximum for cost control
        return min(base_budget, 1024)
    
    def _suggest_preprocessing_strategy(self, text: str, lines: List[str]) -> str:
        """Suggest optimal preprocessing strategy"""
        has_structure = self._has_bullet_points(lines) or self._has_numbered_lists(lines)
        complexity = self._assess_complexity(text, lines)
        content_type = self._detect_content_type(text, lines)
        
        if not has_structure and complexity == "low":
            return "minimal"  # Basic cleanup only
        elif has_structure and complexity == "low":
            return "structural"  # Focus on list conversion
        elif complexity == "medium":
            return "enhanced"  # Smart preprocessing
        else:
            return "comprehensive"  # Full LLM preprocessing
    
    def _estimate_speech_time(self, text: str) -> float:
        """Estimate speech duration in seconds (rough approximation)"""
        # Average speaking rate: ~150 words per minute
        word_count = len(text.split())
        return (word_count / 150) * 60
    
    def get_preprocessing_prompt_template(self, content_type: str, style: str = "natural") -> str:
        """Get appropriate preprocessing prompt template for content type"""
        
        base_templates = {
            "instructions": f"""
Transform these step-by-step instructions into clear, spoken directions using a {style} style:

{{text}}

RULES:
- Convert numbered/bulleted steps into flowing instructions
- Use transition words: "First,", "Next,", "Then,", "Finally,"
- Make it sound like someone giving helpful directions
- Keep all important details and sequence
- End with encouraging completion phrase

Generate natural speech text:""",
            
            "features": f"""
Transform this feature list into engaging spoken content using a {style} style:

{{text}}

RULES:
- Convert bullets into flowing benefits description
- Use connecting phrases: "This includes", "You'll also get", "Additionally,"
- Emphasize value and benefits to the listener
- Make it sound like an enthusiastic presentation
- Group related features naturally

Generate natural speech text:""",
            
            "options": f"""
Transform these options into clear spoken choices using a {style} style:

{{text}}

RULES:
- Convert list into spoken alternatives
- Use choice language: "You can choose", "Another option is", "Alternatively,"
- Present options as helpful guidance
- Make decision-making clear and easy
- End with guidance on next steps

Generate natural speech text:""",
            
            "technical": f"""
Transform this technical content into clear spoken explanation using a {style} style:

{{text}}

RULES:
- Simplify technical jargon where possible
- Spell out acronyms and abbreviations
- Convert symbols and special characters to words
- Use explanatory phrases for complex concepts
- Make it accessible to general audience

Generate natural speech text:""",
            
            "qa": f"""
Transform this Q&A content into natural conversational speech using a {style} style:

{{text}}

RULES:
- Present questions naturally: "You might be wondering..."
- Flow answers conversationally
- Use bridging phrases between Q&As
- Make it sound like helpful dialogue
- Maintain question-answer structure

Generate natural speech text:""",
            
            "general": f"""
Transform this content into natural spoken language using a {style} style:

{{text}}

RULES:
- Convert any structured elements to flowing text
- Add appropriate transitions between ideas
- Make it sound conversational and engaging
- Preserve all important information
- Use natural speech patterns

Generate natural speech text:"""
        }
        
        return base_templates.get(content_type, base_templates["general"])