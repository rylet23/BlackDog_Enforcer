import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
import os
from PIL import UnidentifiedImageError
import random
class SafeImageFolder(datasets.ImageFolder):
    def __getitem__(self, index):
        for _ in range(20): # Try 20 different images if one is bad
            try:
                path, target = self.samples[index]
                sample = self.loader(path)
                if self.transform is not None:
                    sample = self.transform(sample)
                return sample, target
            except Exception as e:
                # This catches the .py file or any corrupt jpegs
                index = random.randint(0, len(self) - 1)
        
        # Absolute fallback: return a blank image so the batch doesn't fail
        return torch.zeros(3, 224, 224), 0
# 1. Setup Data Paths
data_dir = os.path.expanduser("~/BlackDog_Enforcer/Train_Data")

# 2. Advanced Transforms for High Accuracy
# We use 224x224 and data augmentation to make the model "rugged"
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2), # Helps with different lighting
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 3. Load the Dataset
# ImageFolder assigns labels based on the top-level folders: 'animal' and 'not_animal'
full_dataset = SafeImageFolder(root=data_dir, transform=transform)

# Show the mapping to confirm (Should be {'animal': 0, 'not_animal': 1} or vice versa)
print(f"Class Mapping: {full_dataset.class_to_idx}")
animal_idx = full_dataset.class_to_idx['animal']

train_loader = DataLoader(full_dataset, batch_size=16, shuffle=True)

# 4. Use a Powerful "Brain": MobileNetV2
# It's pre-trained on millions of images, so it already knows what 'fur' and 'legs' look like
model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)

# Adjust the final layer for Binary Classification (Animal vs Not Animal)
model.classifier[1] = nn.Sequential(
    nn.Linear(model.last_channel, 1),
    nn.Sigmoid()
)

device = torch.device("cpu") # Pi 5 handles this fine
model.to(device)

# 5. Training Setup
criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.0001) # Slower learning rate for better depth

# 6. Training Loop
print(f"Training on {len(full_dataset)} total images...")
model.train()

for epoch in range(5): # 5-10 epochs for high accuracy
    running_loss = 0.0
    for i, (inputs, labels) in enumerate(train_loader):
        # Force labels to be binary: 1 for animal, 0 for not_animal
        # If ImageFolder assigned 'animal' as 0, we flip them
        binary_labels = (labels == animal_idx).float().unsqueeze(1)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, binary_labels)
        loss.backward()
        optimizer.step()

        if i % 10 == 0:
            print(f"Epoch {epoch+1}, Step {i}, Loss: {loss.item():.4f}")

# 7. Save the Brain
torch.save(model.state_dict(), 'animal_classifier.pth')
print("Finished! New 'In-Depth' model saved.")
