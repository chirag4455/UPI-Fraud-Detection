# Training Configuration for UPI Fraud Detection

# Dataset Paths
DATASET_PATHS = {
    'dataset1': r'D:\Major Project\Datasets',
    'dataset2': r'D:\Major Project\MLBFD_Phase1\Data',
    'dataset3': r'D:\Major Project\MLBFD_Phase2\Data',
}

# Model Hyperparameters
MODEL_HYPERPARAMETERS = {
    'XGBoost': {'learning_rate': 0.1, 'n_estimators': 100, 'max_depth': 5},
    'Random Forest': {'n_estimators': 100, 'max_depth': None},
    'Logistic Regression': {'C': 1.0, 'solver': 'liblinear'},
    'Isolation Forest': {'contamination': 0.1},
    'Neural Network': {'layers': [64, 32], 'activation': 'relu', 'optimizer': 'adam'},
    'LSTM': {'units': 50, 'dropout': 0.2},
}

# Training Parameters
TRAINING_PARAMETERS = {
    'epochs': 50,
    'batch_size': 32,
    'test_size': 0.2,
}

# Features List
FEATURES = [
    'transaction_amount',
    'time',
    'payee_details',
    'device_info',
    'behavioral_features',
    # Add more features as needed
    # Assuming there are 57 features in total
]