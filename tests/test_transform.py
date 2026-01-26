from taxa.transform import flatten_taxon_ancestry


def test_flatten_taxon_ancestry_extracts_all_ranks():
    """Test that flatten_taxon_ancestry extracts all ranks from ancestry."""
    taxon = {
        'id': 12345,
        'name': 'Prunus armeniaca',
        'rank': 'species',
        'is_active': True,
        'iconic_taxon_name': 'Plantae',
        'preferred_common_name': 'Apricot',
        'ancestors': [
            {'id': 1, 'name': 'Plantae', 'rank': 'kingdom'},
            {'id': 2, 'name': 'Magnoliophyta', 'rank': 'phylum'},
            {'id': 3, 'name': 'Magnoliopsida', 'rank': 'class'},
            {'id': 4, 'name': 'Rosales', 'rank': 'order'},
            {'id': 5, 'name': 'Rosaceae', 'rank': 'family'},
            {'id': 6, 'name': 'Amygdaloideae', 'rank': 'subfamily'},
            {'id': 7, 'name': 'Amygdaleae', 'rank': 'tribe'},
            {'id': 8, 'name': 'Prunus', 'rank': 'genus'},
        ]
    }

    result = flatten_taxon_ancestry(taxon)

    assert result['id'] == 12345
    assert result['scientific_name'] == 'Prunus armeniaca'
    assert result['rank'] == 'species'
    assert result['common_name'] == 'Apricot'
    assert result['kingdom'] == 'Plantae'
    assert result['phylum'] == 'Magnoliophyta'
    assert result['class'] == 'Magnoliopsida'
    assert result['order_name'] == 'Rosales'
    assert result['family'] == 'Rosaceae'
    assert result['subfamily'] == 'Amygdaloideae'
    assert result['tribe'] == 'Amygdaleae'
    assert result['genus'] == 'Prunus'
    assert result['is_active'] is True
    assert result['iconic_taxon'] == 'Plantae'


def test_flatten_taxon_ancestry_handles_missing_ranks():
    """Test that missing ranks are set to None."""
    taxon = {
        'id': 456,
        'name': 'Rosaceae',
        'rank': 'family',
        'is_active': True,
        'ancestors': [
            {'id': 1, 'name': 'Plantae', 'rank': 'kingdom'},
            {'id': 4, 'name': 'Rosales', 'rank': 'order'},
        ]
    }

    result = flatten_taxon_ancestry(taxon)

    assert result['kingdom'] == 'Plantae'
    assert result['order_name'] == 'Rosales'
    assert result['family'] == 'Rosaceae'  # Self
    assert result['phylum'] is None
    assert result['class'] is None
    assert result['subfamily'] is None
    assert result['tribe'] is None
    assert result['genus'] is None
