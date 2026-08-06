import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, ConcatDataset
from pathlib import Path

# 1. Paths from your kagglehub output
rodent_path = "/home/blackdog1/.cache/kagglehub/datasets/ojoolasehindeitunu/rodents/versions/4"
not_animal_path = "/home/blackdog1/.cache/kagglehub/datasets/abtabm/multiclassimagedatasetairplanecar/versions/2"

# 2. Data Prep
transform = transforms.Compose([
    transforms.Resize((128, 128)), # Smaller for Pi speed
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Load datasets
# Note: This assumes subfolders exist inside these paths. 
# If they don't, we'll need to point one level deeper.
ds_animal = datasets.ImageFolder(root=rodent_path, transform=transform)
ds_not_animal = datasets.ImageFolder(root=not_animal_path, transform=transform)

# Combine and Load
train_loader = DataLoader(ConcatDataset([ds_animal, ds_not_animal]), batch_size=4, shuffle=True)

# 3. Simple CNN Architecture
class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.main = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(64 * 16 * 16, 128), nn.ReLU(),
            nn.Linear(128, 1), nn.Sigmoid()
        )
    def forward(self, x): return self.main(x)

device = torch.device("cpu")
model = SimpleCNN().to(device)
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.BCELoss()

# 4. Training Loop
print(f"Starting Training: {len(ds_animal)} animals, {len(ds_not_animal)} non-animals.")
model.train()
for epoch in range(3): # 3 Epochs for speed
    running_loss = 0.0
    for i, (inputs, labels) in enumerate(train_loader):
        # Flatten labels to 0/1 (binary) regardless of subfolder count
        binary_labels = (labels > 0).float().unsqueeze(1) 
        
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, binary_labels)
        loss.backward()
        optimizer.step()
        
        if i % 10 == 0:
            print(f"Epoch {epoch+1}, Step {i}, Loss: {loss.item():.4f}")

torch.save(model.state_dict(), 'animal_classifier.pth')
print("Finished! New model saved as animal_classifier.pth")
