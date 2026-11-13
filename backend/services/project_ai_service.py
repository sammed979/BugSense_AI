"""
Project-wide AI analysis service.
Integrates project analysis with existing AI providers (OpenAI, Gemini).
"""

import os
from typing import List, Dict, Optional
from services.ai_service import AIService
from services.log_sense import redact_secrets


class ProjectAIService:
    """Service for AI-powered project analysis."""

    def __init__(self):
        """Initialize the AI service using existing AI integration."""
        self.ai_service = AIService()

    def analyze_issue_with_ai(
        self,
        issue: Dict,
        file_content: str,
        project_context: Dict,
        provider: str = 'openai'
    ) -> Dict:
        """
        Analyze a specific issue using AI.

        Args:
            issue: Issue dictionary from static analysis
            file_content: Content of the affected file
            project_context: Project context (languages, frameworks, etc.)
            provider: AI provider to use ('openai' or 'gemini')

        Returns:
            Enhanced issue with AI analysis
        """
        # Redact sensitive data from file content
        safe_content = redact_secrets(file_content)

        # Prepare context for AI
        context = self._prepare_ai_context(issue, safe_content, project_context)

        # Get AI analysis
        try:
            ai_response = self.ai_service.analyze_code(
                code=safe_content,
                error_message=issue.get('explanation', ''),
                context=context,
                provider=provider
            )

            # Enhance issue with AI insights
            enhanced_issue = issue.copy()
            enhanced_issue.update({
                'ai_explanation': ai_response.get('explanation', ''),
                'ai_root_cause': ai_response.get('root_cause', ''),
                'ai_suggested_solution': ai_response.get('solution', ''),
                'ai_confidence': ai_response.get('confidence', 0),
                'ai_provider': provider,
            })

            return enhanced_issue

        except Exception as e:
            # Return original issue if AI fails
            issue['ai_error'] = str(e)
            return issue

    def analyze_cross_file_issue(
        self,
        files: Dict[str, str],
        issue: Dict,
        project_context: Dict,
        provider: str = 'openai'
    ) -> Dict:
        """
        Analyze cross-file issues using AI.

        Args:
            files: Dictionary of file paths to content
            issue: Cross-file issue dictionary
            project_context: Project context
            provider: AI provider to use

        Returns:
            Enhanced issue with AI analysis
        """
        # Collect relevant files for the issue
        relevant_files = self._collect_relevant_files(files, issue)

        # Redact sensitive data
        safe_files = {
            path: redact_secrets(content)
            for path, content in relevant_files.items()
        }

        # Prepare context
        context = self._prepare_cross_file_context(issue, safe_files, project_context)

        # Get AI analysis
        try:
            ai_response = self.ai_service.analyze_code(
                code='\n\n'.join([f"=== {path} ===\n{content}" for path, content in safe_files.items()]),
                error_message=issue.get('explanation', ''),
                context=context,
                provider=provider
            )

            enhanced_issue = issue.copy()
            enhanced_issue.update({
                'ai_explanation': ai_response.get('explanation', ''),
                'ai_root_cause': ai_response.get('root_cause', ''),
                'ai_suggested_solution': ai_response.get('solution', ''),
                'ai_confidence': ai_response.get('confidence', 0),
                'ai_provider': provider,
            })

            return enhanced_issue

        except Exception as e:
            issue['ai_error'] = str(e)
            return issue

    def generate_repair_suggestion(
        self,
        issue: Dict,
        file_content: str,
        project_context: Dict,
        provider: str = 'openai'
    ) -> Dict:
        """
        Generate a repair suggestion for an issue.

        Args:
            issue: Issue dictionary
            file_content: Current file content
            project_context: Project context
            provider: AI provider to use

        Returns:
            Repair suggestion with original and suggested code
        """
        # Redact sensitive data
        safe_content = redact_secrets(file_content)

        # Prepare repair request
        repair_request = {
            'code': safe_content,
            'error': issue.get('explanation', ''),
            'context': self._prepare_ai_context(issue, safe_content, project_context),
            'file_path': issue.get('affected_file', ''),
            'line_number': issue.get('line_number'),
        }

        try:
            # Use existing repair engine
            from services.repair_engine import RepairEngine
            repair_engine = RepairEngine()

            repair_result = repair_engine.generate_repair(
                source_code=safe_content,
                error_message=issue.get('explanation', ''),
                diagnosis={'issue': issue},
                language='python',  # Will be detected from context
                provider=provider
            )

            return {
                'original_code': file_content,
                'suggested_code': repair_result.get('repaired_code', file_content),
                'explanation': repair_result.get('explanation', ''),
                'diff': repair_result.get('diff', ''),
                'provider': provider,
                'confidence': repair_result.get('confidence', 0),
            }

        except Exception as e:
            return {
                'original_code': file_content,
                'suggested_code': file_content,
                'explanation': f'Failed to generate repair: {str(e)}',
                'diff': '',
                'provider': provider,
                'confidence': 0,
            }

    def _prepare_ai_context(
        self,
        issue: Dict,
        file_content: str,
        project_context: Dict
    ) -> str:
        """Prepare context string for AI analysis."""
        context_parts = [
            f"Project Analysis Context:",
            f"- Languages: {', '.join(project_context.get('languages', []))}",
            f"- Frameworks: {', '.join(project_context.get('frameworks', []))}",
            f"- File: {issue.get('affected_file', 'unknown')}",
            f"- Line: {issue.get('line_number', 'unknown')}",
            f"- Category: {issue.get('category', 'unknown')}",
            f"- Severity: {issue.get('severity', 'unknown')}",
        ]

        if issue.get('related_files'):
            context_parts.append(f"- Related files: {', '.join(issue['related_files'])}")

        return '\n'.join(context_parts)

    def _prepare_cross_file_context(
        self,
        issue: Dict,
        files: Dict[str, str],
        project_context: Dict
    ) -> str:
        """Prepare context for cross-file analysis."""
        context_parts = [
            f"Cross-File Analysis Context:",
            f"- Languages: {', '.join(project_context.get('languages', []))}",
            f"- Frameworks: {', '.join(project_context.get('frameworks', []))}",
            f"- Issue: {issue.get('explanation', 'unknown')}",
            f"- Affected files: {', '.join(files.keys())}",
        ]

        return '\n'.join(context_parts)

    def _collect_relevant_files(
        self,
        files: Dict[str, str],
        issue: Dict
    ) -> Dict[str, str]:
        """Collect files relevant to the issue."""
        relevant = {}

        # Include the affected file
        affected_file = issue.get('affected_file')
        if affected_file and affected_file in files:
            relevant[affected_file] = files[affected_file]

        # Include related files
        for related_file in issue.get('related_files', []):
            if related_file in files:
                relevant[related_file] = files[related_file]

        return relevant

    def analyze_project_with_ai(
        self,
        project_id: int,
        files: Dict[str, str],
        static_issues: List[Dict],
        project_context: Dict,
        provider: str = 'openai',
        max_issues: int = 10
    ) -> List[Dict]:
        """
        Analyze project issues with AI.

        Args:
            project_id: Project ID
            files: Dictionary of file paths to content
            static_issues: List of issues from static analysis
            project_context: Project context
            provider: AI provider to use
            max_issues: Maximum number of issues to analyze with AI

        Returns:
            List of enhanced issues with AI analysis
        """
        enhanced_issues = []

        # Analyze top-priority issues first
        priority_issues = sorted(
            static_issues,
            key=lambda x: self._severity_score(x.get('severity', 'low')),
            reverse=True
        )[:max_issues]

        for issue in priority_issues:
            affected_file = issue.get('affected_file')

            if affected_file and affected_file in files:
                file_content = files[affected_file]

                if issue.get('category') in ['missing_import', 'external_dependency']:
                    # Cross-file issue
                    enhanced = self.analyze_cross_file_issue(
                        files=files,
                        issue=issue,
                        project_context=project_context,
                        provider=provider
                    )
                else:
                    # Single-file issue
                    enhanced = self.analyze_issue_with_ai(
                        issue=issue,
                        file_content=file_content,
                        project_context=project_context,
                        provider=provider
                    )

                enhanced_issues.append(enhanced)
            else:
                # Can't analyze without file content
                enhanced_issues.append(issue)

        # Add remaining issues without AI analysis
        for issue in static_issues:
            if issue not in priority_issues:
                enhanced_issues.append(issue)

        return enhanced_issues

    def _severity_score(self, severity: str) -> int:
        """Convert severity to numeric score for sorting."""
        scores = {
            'critical': 5,
            'high': 4,
            'medium': 3,
            'low': 2,
            'informational': 1,
        }
        return scores.get(severity.lower(), 0)
