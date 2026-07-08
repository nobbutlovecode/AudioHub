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
        """ 
        Thuật toán tái phân phối trọng số động (Bảo toàn tỷ lệ)
        Đảm bảo tổng luôn bằng 1.0 và giữ nguyên giá trị new_value của slider mục tiêu
        """
        weights = base_weights.copy()
        if target_key not in weights:
            return weights
        
        # Đảm bảo giá trị mới nằm trong khoảng an toàn [0, 1]
        new_value = max(0.0, min(1.0, float(new_value)))
        weights[target_key] = new_value
        
        other_keys = [k for k in weights.keys() if k != target_key]
        if not other_keys:
            weights[target_key] = 1.0
            return weights
            
        remaining_sum = 1.0 - new_value
        other_sum = sum(base_weights[k] for k in other_keys)
        
        if other_sum > 0:
            # Phân bổ tỷ lệ thuận theo giá trị cũ của các slider còn lại
            for k in other_keys:
                weights[k] = (base_weights[k] / other_sum) * remaining_sum
        else:
            # Nếu tất cả các slider còn lại đều bằng 0, thực hiện chia đều phần còn lại
            for k in other_keys:
                weights[k] = remaining_sum / len(other_keys)
                
        # Khử sai số dấu phẩy động của máy tính để làm tròn tuyệt đối về 1.0
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

    def generate_driving_advices(self, impedance: float, sensitivity: float) -> dict:
        """Hệ chuyên gia phân tích trở kháng & độ nhạy (Chỉ xuất metadata tư vấn)"""
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
        df_tws["S_price"] = self.normalize_min_max(df_tws["avg_price_vnd"], higher_is_better=False)
        df_tws["S_codec"] = self.normalize_min_max(df_tws["codec_score"], higher_is_better=True)
        df_tws["S_ip"] = df_tws["ip_rating"].apply(self._get_ip_score)
        df_tws["S_sound"] = df_tws["sound_signature"].apply(lambda x: self._calculate_sound_match(x, user_pref))

        # --- ĐỔI MỚI LOGIC CHẤM ĐIỂM ANC ---
        anc_scores = []
        # Lọc danh sách thiết bị có chống ồn dạng cố định (fixed/standard) để tìm biên độ chia điểm số
        fixed_mask = (~df_tws["anc_type"].astype(str).str.strip().str.lower().isin(["none", "adaptive"])) & (df_tws["anc_depth_db"] > 0)
        fixed_devices = df_tws[fixed_mask]
        
        min_fixed = fixed_devices["anc_depth_db"].min() if not fixed_devices.empty else 0
        max_fixed = fixed_devices["anc_depth_db"].max() if not fixed_devices.empty else 0

        for _, row in df_tws.iterrows():
            anc_type = str(row.get("anc_type", "None")).strip().lower()
            anc_depth = float(row.get("anc_depth_db", 0))
            
            if anc_type == "none" or anc_depth == 0:
                anc_scores.append(0.0)
            elif anc_type == "adaptive":
                anc_scores.append(0.8)  # Cố định mức 0.8 cho Adaptive ANC theo yêu cầu
            else:
                # Dành cho Fixed ANC: Chuẩn hóa đưa về không gian [0.4, 1.0] để luôn vượt trội hơn mức None (0.0)
                if max_fixed == min_fixed:
                    anc_scores.append(0.7)
                else:
                    score = 0.4 + 0.6 * (anc_depth - min_fixed) / (max_fixed - min_fixed)
                    anc_scores.append(score)
                    
        df_tws["S_anc"] = pd.Series(anc_scores, index=df_tws.index)

        # Mẫu trọng số mặc định của hệ thống
        default_weights = {
            "w_sound": 0.25, "w_anc": 0.20, "w_battery": 0.15, 
            "w_codec": 0.10, "w_ip": 0.10, "w_price": 0.20
        }

        # --- CHUẨN HÓA TRỌNG SỐ TỪ FRONTEND VỀ TỔNG 1.0 ---
        if custom_weights:
            total_w = sum(custom_weights.values())
            if total_w > 0:
                weights = {k: float(v) / total_w for k, v in custom_weights.items()}
            else:
                weights = default_weights
        else:
            weights = default_weights

        df_tws["Final_score"] = (
            (weights.get("w_sound", 0) * df_tws["S_sound"]) +
            (weights.get("w_anc", 0) * df_tws["S_anc"]) +
            (weights.get("w_battery", 0) * df_tws["S_battery"]) +
            (weights.get("w_codec", 0) * df_tws["S_codec"]) +
            (weights.get("w_ip", 0) * df_tws["S_ip"]) +
            (weights.get("w_price", 0) * df_tws["S_price"])
        )
        return df_tws.sort_values(by="Final_score", ascending=False)

    def score_wired(self, user_pref, custom_weights=None):
        df_wired = self.df[self.df["category"] == "Wired"].copy()
        if df_wired.empty: return df_wired

        df_wired["S_tuning"] = df_wired["sound_signature"].apply(lambda x: self._calculate_sound_match(x, user_pref))
        df_wired["S_driver"] = df_wired.apply(self.get_comprehensive_driver_score, axis=1)
        df_wired["S_sound_total"] = (df_wired["S_tuning"] * 0.60) + (df_wired["S_driver"] * 0.40)
        df_wired["S_price"] = self.normalize_min_max(df_wired["avg_price_vnd"], higher_is_better=False)

        df_wired["Driving_Advice"] = df_wired.apply(
            lambda r: self.generate_driving_advices(
                r["impedance_ohm"], 
                r.get("sensitivity_db", r.get("sensity_db", 100))
            ), axis=1
        )

        default_weights = {"w_sound": 0.65, "w_price": 0.35}

        # --- CHUẨN HÓA TRỌNG SỐ TỪ FRONTEND VỀ TỔNG 1.0 ---
        if custom_weights:
            total_w = sum(custom_weights.values())
            if total_w > 0:
                weights = {k: float(v) / total_w for k, v in custom_weights.items()}
            else:
                weights = default_weights
        else:
            weights = default_weights

        df_wired["Final_score"] = (
            (weights.get("w_sound", 0) * df_wired["S_sound_total"]) +
            (weights.get("w_price", 0) * df_wired["S_price"])
        )
        return df_wired.sort_values(by="Final_score", ascending=False)

    def score_speaker(self, user_pref, custom_weights=None):
        df_speaker = self.df[self.df["category"] == "Speaker"].copy()
        if df_speaker.empty: return df_speaker

        df_speaker["S_sound"] = df_speaker["sound_signature"].apply(lambda x: self._calculate_sound_match(x, user_pref))
        df_speaker["S_power"] = self.normalize_min_max(df_speaker["power_watts"], higher_is_better=True)
        df_speaker["S_battery"] = self.normalize_min_max(df_speaker["battery_life_total"], higher_is_better=True)
        df_speaker["S_ip"] = df_speaker["ip_rating"].apply(self._get_ip_score)
        df_speaker["S_price"] = self.normalize_min_max(df_speaker["avg_price_vnd"], higher_is_better=False)

        default_weights = {
            "w_sound": 0.25, "w_power": 0.25, "w_battery": 0.15, "w_ip": 0.15, "w_price": 0.20
        }

        # --- CHUẨN HÓA TRỌNG SỐ TỪ FRONTEND VỀ TỔNG 1.0 ---
        if custom_weights:
            total_w = sum(custom_weights.values())
            if total_w > 0:
                weights = {k: float(v) / total_w for k, v in custom_weights.items()}
            else:
                weights = default_weights
        else:
            weights = default_weights

        df_speaker["Final_score"] = (
            (weights.get("w_sound", 0) * df_speaker["S_sound"]) +
            (weights.get("w_power", 0) * df_speaker["S_power"]) +
            (weights.get("w_battery", 0) * df_speaker["S_battery"]) +
            (weights.get("w_ip", 0) * df_speaker["S_ip"]) +
            (weights.get("w_price", 0) * df_speaker["S_price"])
        )
        return df_speaker.sort_values(by="Final_score", ascending=False)

                    
# --- KHỐI ĐIỀU KHIỂN KIỂM THỬ TOÀN DIỆN MỚI ---
if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', lambda x: '%.3f' % x)

    print("="*90)
    print("🚀 AUDIOHUB CORE ENGINE - FIXED VERSION TESTING")
    print("="*90)

    rich_mock_data = {
        "category": ["TWS", "TWS", "TWS", "Wired", "Wired", "Wired", "Wired", "Speaker", "Speaker"],
        "model_name": [
            "Sony WF-1000XM5", "Apple AirPods Pro 2", "Moondrop Space Travel",
            "Moondrop Aria 2", "Sennheiser IE 200", "Beyerdynamic DT 990 Pro", "Letshuoer S12 Pro",
            "JBL Charge 5", "Marshall Acton III"
        ],
        "brand": ["Sony", "Apple", "Moondrop", "Moondrop", "Sennheiser", "Beyerdynamic", "Letshuoer", "JBL", "Marshall"],
        "sound_signature": ["Warm", "Neutral", "V-Shape", "Harman", "Neutral", "Bright", "V-Shape", "Bass-heavy", "Warm"],
        "avg_price_vnd": [6250000, 5750000, 790000, 2150000, 3750000, 5500000, 3400000, 3950000, 7800000],
        "anc_depth_db": [39, 39, 35, 0, 0, 0, 0, 0, 0],
        "anc_type": ["Adaptive", "Adaptive", "Standard", "None", "None", "None", "None", "None", "None"],
        "battery_life_total": [24, 30, 12, 0, 0, 0, 0, 20, 0], 
        "codec_score": [5, 2, 2, 0, 0, 0, 0, 0, 0],             
        "ip_rating": ["IPX4", "IPX4", "None", "None", "None", "None", "None", "IP67", "None"],
        "impedance_ohm": [0, 0, 0, 32, 18, 250, 16, 0, 0],
        "sensity_db": [0, 0, 0, 102, 119, 96, 102, 0, 0],       
        "driver_type": ["Dynamic", "Dynamic", "Dynamic", "Single DD", "Dynamic", "Dynamic", "Planar Magnetic", "Dynamic Woofer", "Custom Dynamic"],
        "driver_material": ["PET", "Standard", "Titanium", "LCP", "LCP Polymer", "Standard", "Titanium", "Standard", "Standard"],
        "power_watts": [0, 0, 0, 0, 0, 0, 0, 40, 60]
    }

    df = pd.DataFrame(rich_mock_data)
    recommender = AudioRecommender(df)

    # Thử nghiệm gửi bộ trọng số chưa chuẩn hóa (Thang 0-100 từ Slider)
    unnormalized_frontend_weights = {
        "w_sound": 80, "w_anc": 60, "w_battery": 40, "w_codec": 20, "w_ip": 20, "w_price": 50
    }

    print("\n🔍 [DANH MỤC: TWS] Kiểm thử với Trọng số thô từ Frontend (Tổng khác 1.0) | Gu âm: 'Warm'")
    res_tws = recommender.score_tws(user_pref="Warm", custom_weights=unnormalized_frontend_weights)
    tws_cols = ["model_name", "anc_type", "anc_depth_db", "avg_price_vnd", "S_sound", "S_anc", "S_price", "Final_score"]
    print(res_tws[tws_cols].to_string(index=False))

    print("\n" + "-"*90)
    print("🔍 [DANH MỤC: WIRED] Kiểm thử với thuộc tính 'avg_price_vnd' mới | Gu âm: 'Neutral'")
    res_wired = recommender.score_wired(user_pref="Neutral")
    wired_cols = ["model_name", "sound_signature", "avg_price_vnd", "S_sound_total", "S_price", "Final_score"]
    print(res_wired[wired_cols].to_string(index=False))
    print("="*90)