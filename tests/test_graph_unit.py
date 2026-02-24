from matplotlib.figure import Figure

from solver import graph


def _single_var_result() -> dict:
    return {
        "equation": "2x + 2 = 5",
        "given": {
            "inputs": {
                "equation": "2x + 2 = 5",
                "left_side": "2x + 2",
                "right_side": "5",
                "variable": "x",
            }
        },
        "final_answer": "x = 1.5",
    }


def _two_var_result() -> dict:
    return {
        "equation": "2x + y = 6",
        "given": {
            "inputs": {
                "equation": "2x + y = 6",
                "variables": "x, y",
            }
        },
        "final_answer": "Infinite solutions",
    }


def _system_result() -> dict:
    return {
        "equation": "x + y = 10, x - y = 2",
        "given": {
            "inputs": {
                "equations": "x + y = 10, x - y = 2",
                "variables": "x, y",
            }
        },
        "final_answer": "x = 6\ny = 4",
    }


def test_set_theme_and_text_figure_and_style_axes() -> None:
    graph.set_theme("light")
    assert graph.C_BG == graph._LIGHT_GRAPH["C_BG"]

    fig = Figure(figsize=(4, 2))
    ax = fig.add_subplot(111)
    graph._style_axes(ax, fig)
    assert ax.get_xlabel() == ""

    txt_fig = graph._text_figure("Title", "Message")
    assert isinstance(txt_fig, Figure)


def test_parse_eq_valid_and_invalid() -> None:
    lhs, rhs, local = graph._parse_eq("2x + 1 = 5")
    assert str(lhs) == "2*x + 1"
    assert str(rhs) == "5"
    assert "x" in local

    try:
        graph._parse_eq("2x + 1")
        raised = False
    except ValueError:
        raised = True
    assert raised is True


def test_analysis_helpers_all_cases() -> None:
    single = graph._analyze_single_var({"equation": "2x+2=5", "variable": "x"}, "x = 1.5")
    assert single["case"] == "one_solution"

    two_var = graph._analyze_two_var({"equation": "2x+y=6", "variables": "x, y"}, "")
    assert two_var["eq_type"] == "two_var"

    system = graph._analyze_system({"equations": "x+y=10, x-y=2", "variables": "x, y"}, "x = 6\ny = 4")
    assert system["case"] == "one_solution"

    payload = {"form": "sqrt(x) + pi", "description": "pi"}
    graph._prettify_analysis(payload)
    assert "√(" in payload["form"]
    assert "π" in payload["description"]


def test_analyze_result_dispatch() -> None:
    assert graph.analyze_result(_single_var_result())["eq_type"] == "single_var"
    assert graph.analyze_result(_two_var_result())["eq_type"] == "two_var"
    assert graph.analyze_result(_system_result())["eq_type"] == "system"


def test_build_figure_and_restyle() -> None:
    fig = graph.build_figure(_single_var_result())
    assert isinstance(fig, Figure)

    graph.restyle_figure(fig, "dark")
    assert fig is not None


def test_direct_builders_smoke() -> None:
    fig1 = graph._build_single_var(
        {
            "equation": "2x + 2 = 5",
            "left_side": "2x + 2",
            "right_side": "5",
            "variable": "x",
        },
        "x = 1.5",
    )
    assert isinstance(fig1, Figure)

    fig2 = graph._build_two_var({"equation": "2x + y = 6", "variables": "x, y"}, "")
    assert isinstance(fig2, Figure)

    fig3 = graph._build_multi_var_projection(
        {"equation": "x + y + z = 3", "variables": "x, y, z"}, ""
    )
    assert isinstance(fig3, Figure)

    fig4 = graph._build_single_var_system(
        {"equations": "x = 1, x = 1", "variables": "x"}, "Infinite solutions", "x"
    )
    assert isinstance(fig4, Figure)

    fig5 = graph._build_system({"equations": "x+y=10, x-y=2", "variables": "x, y"}, "x = 6\ny = 4")
    assert isinstance(fig5, Figure)
