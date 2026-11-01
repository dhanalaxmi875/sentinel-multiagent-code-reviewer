"""Unit tests for metrics.py using hand-crafted fixtures."""

import pytest
from eval_harness.metrics import (
    line_ranges_overlap,
    matches_finding_to_label,
    compute_metrics
)


def test_line_ranges_overlap_exact():
    """Test exact line range overlap."""
    assert line_ranges_overlap((10, 20), (15, 25), tolerance=5) is True


def test_line_ranges_overlap_within_tolerance():
    """Test line range overlap within tolerance."""
    assert line_ranges_overlap((10, 20), (26, 30), tolerance=5) is True


def test_line_ranges_overlap_outside_tolerance():
    """Test line range overlap outside tolerance."""
    assert line_ranges_overlap((10, 20), (30, 40), tolerance=5) is False


def test_line_ranges_overlap_none_ranges():
    """Test line range overlap when one or both ranges are None."""
    assert line_ranges_overlap(None, (10, 20), tolerance=5) is True
    assert line_ranges_overlap((10, 20), None, tolerance=5) is True
    assert line_ranges_overlap(None, None, tolerance=5) is True


def test_matches_finding_to_label_perfect_match():
    """Test finding matches label with perfect match."""
    finding = {
        'cwe': 'CWE-89',
        'file': 'src/db.py',
        'line': 15
    }
    label = {
        'cwe': 'CWE-89',
        'file': 'src/db.py',
        'line_range': [10, 20]
    }
    assert matches_finding_to_label(finding, label, tolerance=5) is True


def test_matches_finding_to_label_wrong_cwe():
    """Test finding does not match label with wrong CWE."""
    finding = {
        'cwe': 'CWE-78',
        'file': 'src/db.py',
        'line': 15
    }
    label = {
        'cwe': 'CWE-89',
        'file': 'src/db.py',
        'line_range': [10, 20]
    }
    assert matches_finding_to_label(finding, label, tolerance=5) is False


def test_matches_finding_to_label_wrong_file():
    """Test finding does not match label with wrong file."""
    finding = {
        'cwe': 'CWE-89',
        'file': 'src/other.py',
        'line': 15
    }
    label = {
        'cwe': 'CWE-89',
        'file': 'src/db.py',
        'line_range': [10, 20]
    }
    assert matches_finding_to_label(finding, label, tolerance=5) is False


def test_matches_finding_to_label_line_outside_tolerance():
    """Test finding does not match label when line is outside tolerance."""
    finding = {
        'cwe': 'CWE-89',
        'file': 'src/db.py',
        'line': 50
    }
    label = {
        'cwe': 'CWE-89',
        'file': 'src/db.py',
        'line_range': [10, 20]
    }
    assert matches_finding_to_label(finding, label, tolerance=5) is False


def test_compute_metrics_simple_case():
    """Test metrics computation with simple fixture."""
    manifest = [
        {
            'id': 'sample1',
            'dataset': 'test',
            'language': 'python',
            'file': 'test.py',
            'diff_path': 'diffs/sample1.diff',
            'label': 'vulnerable',
            'cwe': 'CWE-89',
            'line_range': [10, 20]
        },
        {
            'id': 'sample2',
            'dataset': 'test',
            'language': 'python',
            'file': 'test.py',
            'diff_path': 'diffs/sample2.diff',
            'label': 'safe',
            'cwe': 'CWE-89',
            'line_range': None
        }
    ]

    results = {
        'sample1': [
            {
                'cwe': 'CWE-89',
                'file': 'test.py',
                'line': 15
            }
        ],
        'sample2': []
    }

    metrics = compute_metrics(manifest, results, tolerance=5)

    # Verify TP/FP/FN/TN
    assert metrics['overall']['tp'] == 1
    assert metrics['overall']['fp'] == 0
    assert metrics['overall']['fn'] == 0
    assert metrics['overall']['tn'] == 1

    # Verify derived metrics
    assert metrics['overall']['precision'] == 1.0
    assert metrics['overall']['recall'] == 1.0
    assert metrics['overall']['f1'] == 1.0


def test_compute_metrics_with_false_positive():
    """Test metrics computation with false positive on safe sample."""
    manifest = [
        {
            'id': 'sample1',
            'dataset': 'test',
            'language': 'python',
            'file': 'test.py',
            'diff_path': 'diffs/sample1.diff',
            'label': 'safe',
            'cwe': 'CWE-89',
            'line_range': None
        }
    ]

    results = {
        'sample1': [
            {
                'cwe': 'CWE-89',
                'file': 'test.py',
                'line': 10
            }
        ]
    }

    metrics = compute_metrics(manifest, results, tolerance=5)

    assert metrics['overall']['tp'] == 0
    assert metrics['overall']['fp'] == 1
    assert metrics['overall']['fn'] == 0
    assert metrics['overall']['tn'] == 0
    assert metrics['overall']['precision'] == 0.0


def test_compute_metrics_with_false_negative():
    """Test metrics computation with false negative (missed vulnerability)."""
    manifest = [
        {
            'id': 'sample1',
            'dataset': 'test',
            'language': 'python',
            'file': 'test.py',
            'diff_path': 'diffs/sample1.diff',
            'label': 'vulnerable',
            'cwe': 'CWE-89',
            'line_range': [10, 20]
        }
    ]

    results = {
        'sample1': []
    }

    metrics = compute_metrics(manifest, results, tolerance=5)

    assert metrics['overall']['tp'] == 0
    assert metrics['overall']['fp'] == 0
    assert metrics['overall']['fn'] == 1
    assert metrics['overall']['tn'] == 0
    assert metrics['overall']['recall'] == 0.0


def test_compute_metrics_wrong_cwe_on_vulnerable():
    """Test metrics with wrong CWE on vulnerable sample (counts as FP)."""
    manifest = [
        {
            'id': 'sample1',
            'dataset': 'test',
            'language': 'python',
            'file': 'test.py',
            'diff_path': 'diffs/sample1.diff',
            'label': 'vulnerable',
            'cwe': 'CWE-89',
            'line_range': [10, 20]
        }
    ]

    results = {
        'sample1': [
            {
                'cwe': 'CWE-78',  # Wrong CWE
                'file': 'test.py',
                'line': 15
            }
        ]
    }

    metrics = compute_metrics(manifest, results, tolerance=5)

    assert metrics['overall']['tp'] == 0
    assert metrics['overall']['fp'] == 1
    assert metrics['overall']['fn'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
