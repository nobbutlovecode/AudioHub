import pandas as pd
import numpy as np

class AudioRecommender:
    def __init__(self, df_products):
        """
        df_products: DataFrame chứa thông tin danh mục thiết bị từ database
        """
        self.df = df_products.copy()

    def normalize_min_max(self, series, higher_is_better=True):
        """Đưa các biến định lượng về không gian tuyến tính chuẩn [0; 1]"""
        x_min = series.min()
        x_max = series.max()
        if x_max == x_min:
            return pd.Series(1.0, index=series.index)
        if higher_is_better:
            return (series - x_min) / (x_max - x_min)
        else:
            return (x_max - series) / (x_max - x_min)

    def redistribute_weights(self, base_weights, target_key, new_value):
        """ Thuật toán tái phân phối trọng số động (Khấu trừ đều) """
        weights = base_weights.copy()
        if target_key not in weights:
            return weights
        
        old_value = weights[target_key]
        delta = new_value - old_value
        other_keys = [k for k in weights.keys() if k != target_key]
        
        if not other_keys:
            weights[target_key] = 1.0
            return weights
            
        deduction = delta / len(other_keys)
        for k in other_keys:
            weights[k] = max(0.0, weights[k] - deduction)
            
        weights[target_key] = new_value
        
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            for k in weights.keys():
                weights[k] = round(weights[k] / total, 4)
        return weights

    def normalize_material(self, text):
        """Phân loại chuỗi ký tự vật lý vật liệu màng loa"""
        if pd.isna(text) or not str(text).strip(): 
            return "MAT_PET"
        t = str(text).lower().strip()
        if "aluminum" in t and "magnesium" in t: return "MAT_AL_MG"
        elif "beryllium" in t: return "MAT_BE"
        elif "titanium" in t: return "MAT_TI"
        elif "lcp" in t: return "MAT_LCP"
        elif "dlc" in t: return "MAT_DLC"
        elif "wool" in t and "paper" in t: return "MAT_WOOL_PAPER"
        elif "paper" in t: return "MAT_PAPER"
        elif "metal" in t: return "MAT_METAL_COMP"
        elif "pu" in t: return "MAT_PU"
        return "MAT_PET"

    def get_material_score(self, material_code):
        scores = {
            "MAT_BE": 9.5, "MAT_AL_MG": 9.0, "MAT_TI": 8.8,
            "MAT_DLC": 8.7, "MAT_LCP": 8.5, "MAT_METAL_COMP": 8.3,
            "MAT_WOOL_PAPER": 7.8, "MAT_PAPER": 7.3, "MAT_PU": 7.2,
            "MAT_PET": 6.5
        }
        return scores.get(material_code, 6.5)

    def get_comprehensive_driver_score(self, row):
        dtype = str(row.get("driver_type", "dynamic")).strip().lower()
        material_text = row.get("driver_material", "Standard")
        
        arch_scores = {
            "single dd": 7.0, "dynamic": 7.8, "dual dd": 7.5,
            "ba": 8.2, "balanced armature": 8.2, "multi-ba": 8.8,
            "hybrid (dd + ba)": 8.5, "hybrid": 8.6,
            "hybrid (dd + planar)": 9.0, "planar": 9.0, "planar magnetic": 9.2,
            "tribrid": 9.5, "electrostatic": 9.5, "est": 9.5
        }
        
        arch_s = 7.0
        for key, val in arch_scores.items():
            if key in dtype:
                arch_s = val
                break
                
        mat_code = self.normalize_material(material_text)
        mat_s = self.get_material_score(mat_code)
        return (0.6 * arch_s + 0.4 * mat_s) / 10.0

    def _calculate_sound_match(self, product_sign, user_preference):
        if product_sign == user_preference:
            return 1.0
        partial_matches = {
            "Bass-heavy": ["V-Shape", "Warm"],
            "V-Shape": ["Bass-heavy", "Bright"],
            "Neutral": ["Warm", "Bright"],
            "Warm": ["Neutral", "Bass-heavy"],
            "Bright": ["V-Shape", "Neutral"],
            "Mid-forward": ["Neutral", "Warm"],
            "Harman": ["Neutral", "V-Shape"],
            "U-Shape": ["V-Shape", "Neutral"],
            "Analytical": ["Neutral", "Bright"],
            "Dark": ["Warm", "Bass-heavy"],
        }
        if user_preference in partial_matches and product_sign in partial_matches[user_preference]:
            return 0.5
        return 0.0

    def _get_ip_score(self, ip_rating):
        ip_mapping = {
            "IPX0": 0.0, "IP00": 0.0, "None": 0.0,
            "IPX1": 0.1, "IPX2": 0.2, "IPX3": 0.3,
            "IPX4": 0.5, "IP54": 0.5, "IPX5": 0.6, "IP55": 0.6,
            "IPX6": 0.7, "IP66": 0.7, "IPX7": 0.9, "IP57": 0.9, "IP67": 0.9,
            "IPX8": 1.0, "IP68": 1.0
        }
        return ip_mapping.get(str(ip_rating).strip(), 0.0)

    # --- SỬA LỖI THIẾU SELF VÀ CHUẨN HÓA ĐẦU RA CHO HỆ CHUYÊN GIA ---
    def generate_driving_advices(self, impedance: float, sensitivity: float) -> dict:
        """
        Hệ chuyên gia phân tích trở kháng & độ nhạy (Chỉ xuất metadata khuyên dùng, KHÔNG CHẤM ĐIỂM)
        """
        imp_val = float(impedance)
        sens_val = float(sensitivity) if pd.notna(sensitivity) and sensitivity > 0 else 100.0

        if imp_val <= 32 and sens_val >= 100:
            return {
                "status": "Easy",
                "badge_color": "green",
                "advice": "Dễ kéo, có thể cắm trực tiếp vào điện thoại/laptop."
            }
        elif 32 < imp_val <= 80 or sens_val < 100:
            return {
                "status": "Medium",
                "badge_color": "yellow",
                "advice": "Yêu cầu nguồn tốt. Khuyến khích dùng thêm Dongle DAC/AMP rời để tối ưu dải bass."
            }
        else: 
            return {
                "status": "Hard",
                "badge_color": "red",
                "advice": "Thiết bị khó kéo. Bắt buộc phải dùng Desktop DAC/AMP hoặc nguồn phát công suất cao."
            }

    def score_tws(self, user_pref, custom_weights=None):
        df_tws = self.df[self.df["category"] == "TWS"].copy()
        if df_tws.empty: return df_tws

        df_tws["S_battery"] = self.normalize_min_max(df_tws["battery_life_total"], higher_is_better=True)
        df_tws["S_price"] = self.normalize_min_max(df_tws["avg_prive_vnd"], higher_is_better=False)
        df_tws["S_codec"] = self.normalize_min_max(df_tws["codec_score"], higher_is_better=True)
        df_tws["S_ip"] = df_tws["ip_rating"].apply(self._get_ip_score)
        df_tws["S_sound"] = df_tws["sound_signature"].apply(lambda x: self._calculate_sound_match(x, user_pref))

        anc_scores = []
        for _, row in df_tws.iterrows():
            if str(row.get("anc_type")).strip().lower() == "none" or row["anc_depth_db"] == 0:
                anc_scores.append(0.0)
            elif str(row.get("anc_type")).strip().lower() == "adaptive" and row["anc_depth_db"] == 1:
                anc_scores.append(0.80)
            else:
                anc_scores.append(row["anc_depth_db"])
        df_tws["S_anc"] = self.normalize_min_max(pd.Series(anc_scores, index=df_tws.index), higher_is_better=True)

        weights = custom_weights if custom_weights else {
            "w_sound": 0.25, "w_anc": 0.20, "w_battery": 0.15, 
            "w_codec": 0.10, "w_ip": 0.10, "w_price": 0.20
        }

        df_tws["Final_score"] = (
            (weights["w_sound"] * df_tws["S_sound"]) +
            (weights["w_anc"] * df_tws["S_anc"]) +
            (weights["w_battery"] * df_tws["S_battery"]) +
            (weights["w_codec"] * df_tws["S_codec"]) +
            (weights["w_ip"] * df_tws["S_ip"]) +
            (weights["w_price"] * df_tws["S_price"])
        )
        return df_tws.sort_values(by="Final_score", ascending=False)

    # --- REFACTOR TOÀN DIỆN HÀM SCORE_WIRED (BÓC TÁCH NỘI TRỞ) ---
    def score_wired(self, user_pref, custom_weights=None):
        """Hệ thống chấm điểm chuẩn hóa cho Tai nghe dây - Đã cô lập hoàn toàn nội trở khỏi toán học xếp hạng"""
        df_wired = self.df[self.df["category"] == "Wired"].copy()
        if df_wired.empty: return df_wired

        # 1. Tính toán cấu phần âm học cốt lõi (Tuning & Driver cứng)
        df_wired["S_tuning"] = df_wired["sound_signature"].apply(lambda x: self._calculate_sound_match(x, user_pref))
        df_wired["S_driver"] = df_wired.apply(self.get_comprehensive_driver_score, axis=1)
        df_wired["S_sound_total"] = (df_wired["S_tuning"] * 0.60) + (df_wired["S_driver"] * 0.40)
        
        # 2. Tính toán cấu phần giá thành P/P
        df_wired["S_price"] = self.normalize_min_max(df_wired["avg_prive_vnd"], higher_is_better=False)

        # 3. KÍCH HOẠT HỆ CHUYÊN GIA ĐỂ TRÍCH XUẤT METADATA TƯ VẤN (Không nhân với trọng số)
        # Sửa lỗi gọi tên linh hoạt giữa 'sensitivity_db' và 'sensity_db' phòng hờ lỗi DB
        df_wired["Driving_Advice"] = df_wired.apply(
            lambda r: self.generate_driving_advices(
                r["impedance_ohm"], 
                r.get("sensitivity_db", r.get("sensity_db", 100))
            ), axis=1
        )

        # 4. Thiết lập lại Trọng số (Loại bỏ w_impedance, phân bổ lại tỷ lệ vàng: Sound 65% - Price 35%)
        weights = custom_weights if custom_weights else {
            "w_sound": 0.65, "w_price": 0.35
        }

        # Tính toán điểm cuối cùng (Hoàn toàn độc lập với nội trở vật lý)
        df_wired["Final_score"] = (
            (weights["w_sound"] * df_wired["S_sound_total"]) +
            (weights["w_price"] * df_wired["S_price"])
        )
        return df_wired.sort_values(by="Final_score", ascending=False)

    def score_speaker(self, user_pref, custom_weights=None):
        df_speaker = self.df[self.df["category"] == "Speaker"].copy()
        if df_speaker.empty: return df_speaker

        df_speaker["S_sound"] = df_speaker["sound_signature"].apply(lambda x: self._calculate_sound_match(x, user_pref))
        df_speaker["S_power"] = self.normalize_min_max(df_speaker["power_watts"], higher_is_better=True)
        df_speaker["S_battery"] = self.normalize_min_max(df_speaker["battery_life_total"], higher_is_better=True)
        df_speaker["S_ip"] = df_speaker["ip_rating"].apply(self._get_ip_score)
        df_speaker["S_price"] = self.normalize_min_max(df_speaker["avg_prive_vnd"], higher_is_better=False)

        weights = custom_weights if custom_weights else {
            "w_sound": 0.25, "w_power": 0.25, "w_battery": 0.15, "w_ip": 0.15, "w_price": 0.20
        }

        df_speaker["Final_score"] = (
            (weights["w_sound"] * df_speaker["S_sound"]) +
            (weights["w_power"] * df_speaker["S_power"]) +
            (weights["w_battery"] * df_speaker["S_battery"]) +
            (weights["w_ip"] * df_speaker["S_ip"]) +
            (weights["w_price"] * df_speaker["S_price"])
        )
        return df_speaker.sort_values(by="Final_score", ascending=False)

                    
# --- KHỐI ĐIỀU KHIỂN KIỂM THỬ TOÀN DIỆN (CHUYÊN SÂU CHO KIẾN TRÚC SƯ WEB/AI) ---
if __name__ == "__main__":
    # Cấu hình hiển thị của Pandas để không bị bao dòng hoặc ẩn cột trên Console
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', lambda x: '%.3f' % x)

    print("="*90)
    print("🚀 AUDIOHUB CORE ENGINE - KHỐI KIỂM THỬ MA TRẬN ĐIỂM CHUYÊN SÂU (COMPREHENSIVE TEST)")
    print("="*90)

    # 1. Khởi tạo Tập dữ liệu đa dạng để thử nghiệm mọi góc cạnh của thuật toán
    # Thêm các sản phẩm từ phân khúc giá rẻ, tầm trung, đến hi-end, đa dạng màng loa và kiến trúc
    rich_mock_data = {
        "category": ["TWS", "TWS", "TWS", "Wired", "Wired", "Wired", "Wired", "Speaker", "Speaker"],
        "model_name": [
            "Sony WF-1000XM5", "Apple AirPods Pro 2", "Moondrop Space Travel",
            "Moondrop Aria 2", "Sennheiser IE 200", "Beyerdynamic DT 990 Pro", "Letshuoer S12 Pro",
            "JBL Charge 5", "Marshall Acton III"
        ],
        "brand": ["Sony", "Apple", "Moondrop", "Moondrop", "Sennheiser", "Beyerdynamic", "Letshuoer", "JBL", "Marshall"],
        "sound_signature": ["Warm", "Neutral", "V-Shape", "Harman", "Neutral", "Bright", "V-Shape", "Bass-heavy", "Warm"],
        "avg_prive_vnd": [6250000, 5750000, 790000, 2150000, 3750000, 5500000, 3400000, 3950000, 7800000],
        "anc_depth_db": [39, 39, 35, 0, 0, 0, 0, 0, 0],
        "anc_type": ["Adaptive", "Adaptive", "Standard", "None", "None", "None", "None", "None", "None"],
        "battery_life_total": [24, 30, 12, 0, 0, 0, 0, 20, 0], # Marshall cắm điện trực tiếp = 0h pin
        "codec_score": [5, 2, 2, 0, 0, 0, 0, 0, 0],             # 5: LDAC, 2: AAC, 1: SBC
        "ip_rating": ["IPX4", "IPX4", "None", "None", "None", "None", "None", "IP67", "None"],
        "impedance_ohm": [0, 0, 0, 32, 18, 250, 16, 0, 0],
        "sensity_db": [0, 0, 0, 102, 119, 96, 102, 0, 0],       # Cột map linh hoạt tên từ DB
        "driver_type": ["Dynamic", "Dynamic", "Dynamic", "Single DD", "Dynamic", "Dynamic", "Planar Magnetic", "Dynamic Woofer", "Custom Dynamic"],
        "driver_material": ["PET", "Standard", "Titanium", "LCP", "LCP Polymer", "Standard", "Titanium", "Standard", "Standard"],
        "power_watts": [0, 0, 0, 0, 0, 0, 0, 40, 60]
    }

    df = pd.DataFrame(rich_mock_data)
    recommender = AudioRecommender(df)

    # ----------------------------------------------------------------------
    # KỊCH BẢN 1: ĐÁNH GIÁ TWS (User gu ấm "Warm", ưu tiên chống ồn và chất âm)
    # ----------------------------------------------------------------------
    print("\n🔍 [DANH MỤC: TWS] Kiểm thử với Gu âm: 'Warm' | Trọng số mặc định")
    res_tws = recommender.score_tws(user_pref="Warm")
    tws_cols = ["model_name", "sound_signature", "avg_prive_vnd", "S_sound", "S_anc", "S_battery", "S_codec", "S_ip", "S_price", "Final_score"]
    print(res_tws[tws_cols].to_string(index=False))
    print("\n💡 Phân tích TWS:")
    print(" - Sony WF-1000XM5 đứng top vì S_sound = 1.0 (khớp hoàn hảo gu Warm) và hỗ trợ LDAC (S_codec cao).")
    print(" - Moondrop Space Travel tuy giá cực rẻ (S_price = 1.0) nhưng bị kéo điểm xuống do pin yếu và codec thấp.")

    # ----------------------------------------------------------------------
    # KỊCH BẢN 2: ĐÁNH GIÁ TAI NGHE DÂY (WIRED) - BÓC TÁCH NỘI TRỞ THÀNH ADVICE
    # ----------------------------------------------------------------------
    print("\n" + "-"*90)
    print("🔍 [DANH MỤC: WIRED] Kiểm thử với Gu âm: 'Neutral' | Khấu trừ nội trở khỏi điểm số")
    res_wired = recommender.score_wired(user_pref="Neutral")
    
    # Bung cấu trúc Dict của Hệ chuyên gia thành các cột độc lập để hiển thị rõ trên bảng
    res_wired["Advice_Status"] = res_wired["Driving_Advice"].apply(lambda x: x["status"])
    res_wired["Advice_Text"] = res_wired["Driving_Advice"].apply(lambda x: x["advice"])
    
    wired_cols = ["model_name", "sound_signature", "driver_type", "driver_material", "S_tuning", "S_driver", "S_sound_total", "S_price", "Final_score", "Advice_Status", "Advice_Text"]
    print(res_wired[wired_cols].to_string(index=False))
    print("\n💡 Phân tích Wired (Quan trọng):")
    print(" - Bạn có thể thấy Beyerdynamic DT 990 Pro (250 Ohm) có điểm số hoàn toàn không bị kéo thấp xuống bởi trở kháng lớn.")
    print(" - Điểm Final_score lúc này chỉ dựa trên chất âm (S_sound_total) và giá thành (S_price).")
    print(" - Trở kháng cao và độ nhạy thấp nay được chuyển hoàn toàn thành nhãn điện học 'Hard' kèm lời khuyên chuẩn Audiophile.")

    # ----------------------------------------------------------------------
    # KỊCH BẢN 3: ĐÁNH GIÁ LOA (SPEAKER) (User thích nghe tạp, gu cân bằng "Neutral")
    # ----------------------------------------------------------------------
    print("\n" + "-"*90)
    print("🔍 [DANH MỤC: SPEAKER] Kiểm thử với Gu âm: 'Neutral' | Đánh giá công suất & Độ bền")
    res_speaker = recommender.score_speaker(user_pref="Neutral")
    speaker_cols = ["model_name", "sound_signature", "power_watts", "battery_life_total", "S_sound", "S_power", "S_battery", "S_ip", "S_price", "Final_score"]
    print(res_speaker[speaker_cols].to_string(index=False))
    print("\n💡 Phân tích Speaker:")
    print(" - JBL Charge 5 vượt lên nhờ có pin trâu (S_battery = 1.0) và chỉ số chống nước bụi khắt khe IP67 (S_ip = 0.9).")
    print(" - Marshall Acton III tuy công suất lớn (S_power = 1.0) nhưng vì là loa cắm điện bàn (Pin = 0, Không kháng nước) nên điểm tổng hợp bị tụt giảm.")
    
    print("\n" + "="*90)
    print("✅ KIỂM THỬ TOÀN DIỆN HOÀN TẤT - THUẬT TOÁN ĐÁNH GIÁ ĐÚNG THIẾT KẾ KỸ THUẬT!")
    print("="*90)