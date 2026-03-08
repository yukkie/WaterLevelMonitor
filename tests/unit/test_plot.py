import matplotlib.pyplot as plt
import pandas as pd

from src.plot import plot_water_level


def test_plot_water_level_execution_and_data(test_config):
    """
    plot_water_level関数が正しくFigureを返し、内部のデータ変換が期待通りかテストする。
    """
    dam_config = test_config.sites["miyagase"].dam
    rain_config = test_config.sites["miyagase"].rain

    # ダミーのダムデータ (10分間隔)
    base_time = pd.Timestamp("2023-10-01T00:00:00Z")
    times = [base_time + pd.Timedelta(minutes=10 * i) for i in range(12)]  # 2時間分

    # 意図的に欠損値(NaN)を入れる
    dam_data = {
        "timestamp": times,
        "volume": [10000 + i * 10 for i in range(11)] + [float("nan")],
        "inflow": [10.0 + i for i in range(12)],
        "outflow": [5.0 for i in range(12)],
    }
    dam_df = pd.DataFrame(dam_data)

    # ダミーの雨量データ (10分間隔)
    # 欠損値(NaN)や0.0のデータを入れる
    rain_data = {
        "timestamp": times,
        "rainfall": [1.0, 0.0, 1.0, float("nan"), 2.0, 0.5]
        + [0.0] * 6,  # 最初の1時間: 4.5mm積算, 次の1時間: 0mm
    }
    rain_df = pd.DataFrame(rain_data)

    # Figureオブジェクトが返ってくるかテスト (クラッシュしないこと)
    fig = plot_water_level(dam_config, dam_df, rain_config, rain_df)

    # Axesオブジェクトの検証
    axes = fig.get_axes()
    # add_subplot の順序により ax1, ax3 (subplot由来), ax2 (twinx由来) となる
    assert len(axes) == 3
    ax1, ax3, ax2 = axes

    # --- データ変換の検証 ---

    # 雨量 (ax2) の1時間積算が機能しているか
    # 棒グラフ(BarContainer)からデータを取得
    bars = [child for child in ax2.get_children() if isinstance(child, plt.Rectangle)]
    # 自動生成される背景などのRectangleを除外するため、高さが0より大きいものを取得
    # (plot.py 内で > 0 にフィルタしているので、1本だけ描画されるはず)
    rain_heights = [
        b.get_height() for b in bars if b.get_height() > 0 and b.get_width() < 1
    ]

    # 最初の1時間の積算雨量は 1.0 + 0.0 + 1.0 + 2.0 + 0.5 = 4.5mm (NaNはスキップ)
    # 次の1時間はすべて0.0なのでプロットから除外される
    assert len(rain_heights) == 1
    assert rain_heights[0] == 4.5

    # 動的Y軸スケールの検証 (ax2)
    ylim = ax2.get_ylim()
    assert ylim[0] == 0  # 下限は0
    # 上限は max(rain_max * 4, 5) -> max(18.0, 5) -> 18.0
    assert ylim[1] == 18.0

    # ダムデータ (ax1) のNaNドロップと貯水率計算
    lines = ax1.get_lines()
    assert len(lines) == 1
    y_data = lines[0].get_ydata()

    # 12個のデータのうち1つ（最後）がNaNなので11個プロットされているはず
    assert len(y_data) == 11

    # 貯水率の計算チェック: (10000 * 1000) / capacity * 100
    # capacity_m3 が仮に 193000000 なら...
    expected_rate = ((dam_data["volume"][0] * 1000) / dam_config.capacity_m3) * 100
    assert abs(y_data[0] - expected_rate) < 0.001

    plt.close(fig)  # メモリリーク防止


def test_plot_japanese_font_warning(test_config, tmp_path):
    """
    グラフ描画時に日本語フォント(豆腐)に関する警告が出ないかを検証する。
    """
    import warnings

    dam_config = test_config.sites["miyagase"].dam
    rain_config = test_config.sites["miyagase"].rain

    # 最低限のダミーデータ
    base_time = pd.Timestamp("2023-10-01T00:00:00Z")
    dam_df = pd.DataFrame(
        {
            "timestamp": [base_time, base_time + pd.Timedelta(minutes=10)],
            "volume": [10000, 10000],
            "inflow": [10.0, 10.0],
            "outflow": [5.0, 5.0],
        }
    )
    rain_df = pd.DataFrame(
        {
            "timestamp": [base_time, base_time + pd.Timedelta(minutes=10)],
            "rainfall": [1.0, 1.0],
        }
    )

    # 実際に描画(savefig)を行って、UserWarning("Glyph XXX missing from font") が出ないかトラップする
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        fig = plot_water_level(dam_config, dam_df, rain_config, rain_df)

        output_file = tmp_path / "test_font.png"
        fig.savefig(str(output_file))
        plt.close(fig)

        glyph_encounters = [
            str(warn.message) for warn in w if "Glyph" in str(warn.message)
        ]

    assert (
        len(glyph_encounters) == 0
    ), f"日本語フォントが見つからず文字化け(豆腐)が発生する可能性があります\\n詳細: {glyph_encounters}"
